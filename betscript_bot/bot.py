"""
bot.py — BetScript Bot (Main Entry Point)
This is the competition API wrapper. Adapt the `act()` function interface
to match whatever platform/API constraints BetScript provides.

Standard interface assumed from PyPokerEngine-compatible platforms:
- Bot must implement declare_action(valid_actions, hole_card, round_state)
- OR equivalent structured game state dict

This bot will auto-detect the call format and dispatch appropriately.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging

from hand_evaluator import card_from_str, parse_hand
from opponent_profiler import OpponentDatabase
from decision_engine import DecisionEngine, GameState
from range_tables import position_label
from tournament_pressure import stack_pressure_factor

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("BetScriptBot")

# ─── Positions ────────────────────────────────────────────────────────────────
POSITIONS_6MAX = ["BTN", "SB", "BB", "UTG", "MP", "CO"]

# ─── Main Bot Class ───────────────────────────────────────────────────────────

class BetScriptBot:
    """
    God-Level BetScript Poker Bot
    Architecture: Hybrid GTO + Bayesian Exploitative
    """

    VERSION = "3.1.0-god-level"
    AUTHOR = "Team BetScript"

    def __init__(self, aggression: str = "balanced"):
        self.db = OpponentDatabase()
        self.engine = DecisionEngine(self.db, aggression=aggression)
        self.our_id: Optional[str] = None
        self.seat: int = 0
        self.hand_count: int = 0
        self._last_street: Optional[str] = None
        self._mode_locked: bool = False   # True after first adaptive switch
        self._last_mode_check: int = 0    # hand_count of last adaptive check

        logger.info(f"BetScriptBot {self.VERSION} initialized. Aggression: {aggression}")

    # ─── PyPokerEngine Compatible Interface ───────────────────────────────────

    def declare_action(
        self,
        valid_actions: List[Dict],
        hole_card: List[str],
        round_state: Dict
    ) -> tuple[str, int]:
        """
        PyPokerEngine interface.
        valid_actions = [{"action":"fold"}, {"action":"call","amount":X}, {"action":"raise","amount":{"min":X,"max":Y}}]
        hole_card = ["Ah", "Kd"]
        round_state = full round state dict
        """
        gs = self._parse_round_state(hole_card, round_state, valid_actions)
        action = self.engine.decide(gs)
        logger.info(f"[H{self.hand_count}] {action.action.upper()} {action.amount:.0f} — {action.reasoning}")

        return self._map_action(action, valid_actions)

    def receive_game_start_message(self, game_info: Dict):
        self.our_id = game_info.get("player_name", "Bot")
        logger.info(f"Game start: players={game_info.get('player_num')}, "
                    f"BB={game_info.get('blind_structure', {}).get('big', '?')}")

    def receive_round_start_message(self, round_count: int, hole_card: List[str], seats: List[Dict]):
        self.hand_count = round_count
        # Record chip counts for all opponents
        for seat in seats:
            pid = seat.get("name", str(seat.get("uuid", "?")))
            if pid != self.our_id:
                self.db.record_chips(pid, seat.get("stack", 0))
        logger.info(f"Round {round_count} | Hole: {' '.join(hole_card)}")

        # v3.1: Adaptive mode switch — triggers at hand 20 then every 50 hands
        hands_since_check = round_count - self._last_mode_check
        if round_count >= 20 and hands_since_check >= 50 or round_count == 20:
            self.adaptive_mode_check()

    def receive_street_start_message(self, street: str, round_state: Dict):
        self._last_street = street
        logger.debug(f"Street: {street}")

    def receive_player_action_message(self, player_uuid: str, action: str, amount: int, round_state: Dict):
        """Track opponent actions for profiling."""
        pid = self._resolve_pid(player_uuid, round_state)
        if pid == self.our_id:
            return

        street = round_state.get("street", "preflop")
        call_amount = self._get_call_amount(round_state)
        raise_facing = call_amount > 0

        if street == "preflop":
            self.db.record_preflop_action(pid, action, facing_raise=raise_facing)
        else:
            pot = sum(p.get("amount", 0) for p in round_state.get("community_pot", [{}]))
            bet_pct = (amount / pot) if pot > 0 else 0
            self.db.record_postflop_action(pid, action, bet_size_pct=bet_pct)

    def receive_game_result_message(self, winners: List[Dict], hand_info: Dict, round_state: Dict):
        """Record showdown results for profiling."""
        shown_hands = hand_info.get("hand", {})
        for player_uuid, hinfo in shown_hands.items():
            pid = self._resolve_pid(player_uuid, round_state)
            if pid == self.our_id:
                continue
            hand_strength = hinfo.get("hand", {}).get("strength", "")
            is_bluff = hand_strength in ("HIGHCARD", "ONEPAIR") and player_uuid not in [w.get("uuid") for w in winners]
            self.db.record_showdown(pid, is_bluff)

    # ─── Generic Dictionary Interface (for custom platforms) ─────────────────

    def act(self, game_state: Dict) -> Dict:
        """
        Generic dict-based interface for custom platforms.
        Expected keys: hole_cards, board, pot, call_amount,
                       our_chips, big_blind, position, street,
                       num_players, active_opponents
        """
        hole = [card_from_str(c) for c in game_state["hole_cards"]]
        board = [card_from_str(c) for c in game_state.get("board", [])]

        gs = GameState(
            hole_cards=hole,
            board=board,
            pot=game_state.get("pot", 0),
            call_amount=game_state.get("call_amount", 0),
            our_chips=game_state.get("our_chips", 1000),
            big_blind=game_state.get("big_blind", 10),
            position=game_state.get("position", "MP"),
            street=game_state.get("street", "preflop"),
            num_players=game_state.get("num_players", 6),
            active_opponents=game_state.get("active_opponents", []),
            last_aggressor=game_state.get("last_aggressor"),
        )

        action = self.engine.decide(gs)
        logger.info(f"ACT: {action.action.upper()} {action.amount} | {action.reasoning}")
        return {"action": action.action, "amount": action.amount, "reasoning": action.reasoning}

    # ─── Internal Helpers ─────────────────────────────────────────────────────

    def _parse_round_state(
        self,
        hole_card: List[str],
        round_state: Dict,
        valid_actions: List[Dict]
    ) -> GameState:
        """Parse PyPokerEngine round_state into our GameState."""
        community = round_state.get("community_card", [])
        street_name = round_state.get("street", "preflop")

        # Pot
        pots = round_state.get("pot", {}).get("main", {})
        pot = pots.get("amount", 0) if isinstance(pots, dict) else 0
        side_pots = round_state.get("pot", {}).get("side", [])
        for sp in side_pots:
            pot += sp.get("amount", 0)

        # Call amount
        call_action = next((a for a in valid_actions if a["action"] == "call"), None)
        call_amount = call_action["amount"] if call_action else 0

        # Our chips
        seats = round_state.get("seats", [])
        our_chips = 0
        active_opponents = []
        for s in seats:
            pid = s.get("name", str(s.get("uuid", "x")))
            if pid == self.our_id:
                our_chips = s.get("stack", 0)
                self.seat = s.get("seat", 0)
            elif s.get("state", "participating") == "participating":
                active_opponents.append(pid)

        # Position
        dealer_btn = round_state.get("dealer_btn", 0)
        num_players = len([s for s in seats if s.get("state") == "participating"])
        rel_pos = (self.seat - dealer_btn) % num_players
        position = POSITIONS_6MAX[rel_pos] if rel_pos < len(POSITIONS_6MAX) else "MP"

        # Big blind
        sb = round_state.get("small_blind_amount", 10)
        big_blind = sb * 2

        # Last aggressor
        action_histories = round_state.get("action_histories", {})
        street_history = action_histories.get(street_name, [])
        last_agg = None
        for ah in reversed(street_history):
            if ah.get("action") in ("raise", "RAISE", "bet", "BET"):
                last_agg = self._resolve_pid(ah.get("uuid", ""), round_state)
                break

        return GameState(
            hole_cards=[card_from_str(c) for c in hole_card],
            board=[card_from_str(c) for c in community],
            pot=pot,
            call_amount=call_amount,
            our_chips=our_chips,
            big_blind=big_blind,
            position=position,
            street=street_name,
            num_players=num_players,
            active_opponents=active_opponents,
            last_aggressor=last_agg
        )

    def _map_action(self, action, valid_actions: List[Dict]) -> tuple[str, int]:
        """Map our action to valid platform action."""
        action_names = {a["action"] for a in valid_actions}

        if action.action == "fold":
            return "fold", 0
        if action.action in ("check",) and "check" in action_names:
            return "check", 0
        if action.action in ("check",) and "call" in action_names:
            return "call", 0  # fallback

        if action.action in ("raise", "bet", "check-raise"):
            raise_action = next((a for a in valid_actions if a["action"] == "raise"), None)
            if raise_action:
                min_r = raise_action.get("amount", {}).get("min", 0)
                max_r = raise_action.get("amount", {}).get("max", 0)
                if isinstance(min_r, (int, float)):
                    amount = max(int(min_r), min(int(action.amount), int(max_r)))
                    return "raise", amount
            # Fallback to call if no raise available
            call_action = next((a for a in valid_actions if a["action"] == "call"), None)
            if call_action:
                return "call", call_action.get("amount", 0)

        if action.action == "call" and "call" in action_names:
            call_action = next(a for a in valid_actions if a["action"] == "call")
            return "call", call_action.get("amount", 0)

        return "fold", 0  # safest fallback

    def _get_call_amount(self, round_state: Dict) -> int:
        """Extract call amount from round_state."""
        for sh in round_state.get("action_histories", {}).values():
            for a in reversed(sh):
                if a.get("action") in ("raise", "RAISE"):
                    return a.get("amount", 0)
        return 0

    def _resolve_pid(self, uuid: str, round_state: Dict) -> str:
        """Resolve UUID to player name."""
        for s in round_state.get("seats", []):
            if s.get("uuid") == uuid:
                return s.get("name", uuid)
        return uuid

    def adaptive_mode_check(self) -> None:
        """
        v3.1: Adaptive aggression mode switching.
        Scores the full opponent field after the 20-hand probe phase.
        Switches engine.aggression to maximize EV against the observed field.

        Scoring rules (derived from v3 strategy exploit tables):
          avg_vpip > 0.38  (passive fish)    -> aggressive  (farm calling stations)
          avg_vpip < 0.18  (nitty tendencies) -> aggressive  (steal their blinds)
          avg_af   > 2.5   (maniacs)          -> balanced    (trap, don't bluff)
          fold_cbet > 0.65                   -> aggressive  (fire cbets freely)
          fold_cbet < 0.30                   -> balanced    (no point bluffing)
          DEFAULT                             -> balanced
        """
        profiles = self.db.all_players()
        if not profiles:
            return  # no data yet

        # Only score opponents with meaningful sample sizes
        meaningful = [p for p in profiles if p.vpip_hands >= 5]
        if not meaningful:
            return

        n = len(meaningful)
        avg_vpip    = sum(p.vpip for p in meaningful) / n
        avg_af      = sum(p.aggression_factor for p in meaningful) / n
        avg_f2cbet  = sum(p.fold_to_cbet for p in meaningful) / n
        avg_f2_3bet = sum(p.fold_to_3bet for p in meaningful) / n

        # --- Decision tree (AF check MUST come before VPIP check) ---
        # Maniacs have both high AF AND high VPIP; AF wins the classification.
        if avg_af > 2.5:
            # Maniac field: they bluff/raise a lot -> trap, don't bluff back
            new_mode = "balanced"
            reason   = f"MANIAC FIELD: avg_af={avg_af:.1f} -- trap & call down"
        elif avg_vpip > 0.38:
            # Passive/fish field: they call too much -> hammer them with value
            new_mode = "aggressive"
            reason   = f"FISH FIELD: avg_vpip={avg_vpip:.0%} -- hammer value bets"
        elif avg_vpip < 0.18 and avg_af < 1.5:
            # Nitty field: they fold too much -> steal their blinds
            new_mode = "aggressive"
            reason   = f"NIT FIELD: avg_vpip={avg_vpip:.0%}, af={avg_af:.1f} -- steal"
        elif avg_f2cbet > 0.65:
            # Folds to cbets: fire every flop
            new_mode = "aggressive"
            reason   = f"HIGH FCB: avg_fcb={avg_f2cbet:.0%} -- cbet wide"
        elif avg_f2cbet < 0.30:
            # Stations: no bluffing, pure value
            new_mode = "balanced"
            reason   = f"STATIONS: avg_fcb={avg_f2cbet:.0%} -- value only, no bluffs"
        else:
            # Mixed/unknown field: GTO-lite
            new_mode = "balanced"
            reason   = f"MIXED FIELD: vpip={avg_vpip:.0%} af={avg_af:.1f} -- default balanced"

        old_mode = self.engine.aggression
        if new_mode != old_mode:
            self.engine.set_aggression(new_mode)
            logger.info(
                f"[ADAPTIVE H{self.hand_count}] Mode: {old_mode.upper()} -> "
                f"{new_mode.upper()} | {reason}"
            )
        else:
            logger.info(
                f"[ADAPTIVE H{self.hand_count}] Mode confirmed: {new_mode.upper()} | {reason}"
            )

        self._last_mode_check = self.hand_count

    def print_stats(self):
        """Print opponent profiling summary."""
        print("\n=== OPPONENT PROFILES ===")
        self.db.print_all()


# ─── CLI Test Interface ───────────────────────────────────────────────────────

if __name__ == "__main__":
    bot = BetScriptBot(aggression="balanced")

    # Test generic dict interface
    result = bot.act({
        "hole_cards": ["As", "Kh"],
        "board": ["Qd", "Jc", "2s"],
        "pot": 400,
        "call_amount": 0,
        "our_chips": 2500,
        "big_blind": 50,
        "position": "BTN",
        "street": "flop",
        "num_players": 3,
        "active_opponents": ["Villain1", "Villain2"],
    })
    print(f"Action: {result['action'].upper()} {result['amount']}")
    print(f"Reasoning: {result['reasoning']}")
