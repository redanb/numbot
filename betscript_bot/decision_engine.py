"""
decision_engine.py — BetScript Bot v3.0
Hybrid GTO + Exploitative decision engine.
Integrates: hand equity, opponent profiles, position, tournament pressure.
Returns the best action (fold/check/call/raise) with sizing.

v3 Upgrades (Verified — betscript_godlevel_strategy.md):
  [1] ICM Bubble Factor Guard: chip-leaders need >52.2% equity to call all-ins
  [2] Multi-way equity discount: avoid over-valuing hands with 3+ opponents
  [3] 20-hand probe gate: play conservative until 20+ hands of opponent data
  [4] SPR commitment logic: auto-commit correct stack-to-pot scenarios
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
import random

from hand_evaluator import (
    equity_monte_carlo, preflop_hand_strength,
    pot_odds, expected_value, parse_hand
)
from range_tables import (
    should_open_raise, should_3bet, open_raise_frequency,
    hand_key, position_label
)
from opponent_profiler import OpponentDatabase, PlayerProfile
from tournament_pressure import (
    stack_pressure_factor, should_push_allin,
    risk_of_ruin_threshold, steal_raise_size
)

# ─── Game State ───────────────────────────────────────────────────────────────

@dataclass
class GameState:
    hole_cards: List[int]         # our 2 hole cards (int list)
    board: List[int]              # community cards (0–5 ints)
    pot: float                    # current pot size
    call_amount: float            # amount to call (0 = check)
    our_chips: float              # our current chip stack
    big_blind: float              # current big blind
    position: str                 # "UTG","MP","CO","BTN","SB","BB"
    street: str                   # "preflop","flop","turn","river"
    num_players: int              # total players at table
    active_opponents: List[str]   # player_ids of active opponents
    already_bet: float = 0.0     # what we've already put in this street
    last_aggressor: Optional[str] = None  # who bet/raised last


# ─── Action Result ─────────────────────────────────────────────────────────────

@dataclass
class Action:
    action: str          # "fold", "check", "call", "raise"
    amount: float = 0.0  # raise amount (total, not increment)
    reasoning: str = ""  # human-readable explanation (for debug/presentation)


# ─── Core Decision Engine ──────────────────────────────────────────────────────

# ─── v3 Constants (ICM Bubble Factor — Python-verified) ──────────────────────
# Malmuth-Harville 3-player ICM @ stacks [1500,1000,500], prizes [70,20,10]
# Losing costs 19.83% equity; winning gains 18.17% — Bubble Factor = 1.092
# Required call equity = BF/(1+BF) = 1.092/2.092 = 52.2%
ICM_CHIP_LEADER_CALL_THRESHOLD = 0.522   # minimum equity to call all-in as chip leader
ICM_BUBBLE_FACTOR = 1.092                # cost of losing / benefit of winning
PROBE_HANDS_REQUIRED = 20               # hands before exiting "probe mode"


class DecisionEngine:

    def __init__(self, opponent_db: OpponentDatabase = None, aggression: str = "balanced"):
        self.db = opponent_db or OpponentDatabase()
        self.aggression = aggression   # "conservative", "balanced", "aggressive"
        self._cbet_count = 0
        self._hands_decided = 0        # tracks how many decisions we've made (probe gate)

    def set_aggression(self, mode: str) -> None:
        """Hot-swap aggression mode at runtime (called after 20-hand probe)."""
        assert mode in ("conservative", "balanced", "aggressive"), f"Unknown mode: {mode}"
        self.aggression = mode

    def decide(self, state: GameState) -> Action:
        """Main entry point. Returns the best Action given the game state."""
        self._hands_decided += 1

        # ── v3: Probe gate — stay conservative for first 20 hands ──
        in_probe_mode = self._hands_decided <= PROBE_HANDS_REQUIRED
        if in_probe_mode and state.street == "preflop":
            return self._decide_preflop(state, probe_mode=True)

        if state.street == "preflop":
            return self._decide_preflop(state)
        else:
            return self._decide_postflop(state)

    def _is_chip_leader(self, our_chips: float, opponents: list) -> bool:
        """Returns True if we have the largest stack vs all active opponents."""
        if not opponents:
            return False
        opp_stacks = [self.db.get(p).chips_history[-1]
                      if self.db.get(p).chips_history else 0
                      for p in opponents]
        return our_chips > max(opp_stacks) if opp_stacks else False

    def _apply_multiway_equity_discount(self, equity: float, num_opponents: int) -> float:
        """
        v3: Multi-way equity discount.
        With 3+ opponents, equity vs field is lower than 1-vs-1 MC estimate.
        Discount by 8% per additional opponent beyond 1.
        """
        if num_opponents <= 1:
            return equity
        discount = 1.0 - (0.08 * (num_opponents - 1))
        return max(0.05, equity * discount)

    def _spr_commitment(self, spr: float, equity: float) -> bool:
        """
        v3: SPR commitment logic (v3 strategy Calc #14).
        SPR < 3 and equity > 43% → commit all-in.
        SPR 3-5 → need two pair+.
        SPR > 8 → need sets/straights/flushes.
        """
        if spr <= 3:
            return equity >= 0.43
        if spr <= 5:
            return equity >= 0.58
        if spr <= 8:
            return equity >= 0.68
        return equity >= 0.78

    # ─── Preflop Decision ─────────────────────────────────────────────────────

    def _decide_preflop(self, state: GameState, probe_mode: bool = False) -> Action:
        gs = state
        pressure = stack_pressure_factor(gs.our_chips, gs.big_blind)

        # Calculate preflop hand strength
        pf_strength = preflop_hand_strength(gs.hole_cards)
        key = hand_key(gs.hole_cards)

        # ── v3: Probe mode — play only top 15% until 20 hands observed ──
        if probe_mode and gs.call_amount > 0 and pf_strength < 0.70:
            return Action("fold", 0, f"PROBE MODE: folding {key} (confidence insufficient)")
        if probe_mode and gs.call_amount == 0:
            return Action("check", 0, "PROBE MODE: check to observe opponent")

        # ── Push/Fold Mode (short stack) ──
        if pressure >= 0.65:
            if should_push_allin(pf_strength, gs.our_chips, gs.big_blind, gs.position):
                return Action("raise", gs.our_chips,
                              f"SHORT STACK PUSH: M={gs.our_chips/(gs.big_blind*1.5):.1f}, "
                              f"strength={pf_strength:.2f}")
            if gs.call_amount == 0:
                return Action("check", 0, "Short stack: check back")
            if gs.call_amount <= gs.big_blind * 0.5:
                return Action("call", gs.call_amount, "Short stack: cheap call")
            return Action("fold", 0, f"Short stack: fold weak hand ({key})")

        # ── Normal Stack Preflop ──
        raise_open_freq = open_raise_frequency(gs.hole_cards, gs.position)

        # Facing a 3-bet
        if gs.call_amount > gs.big_blind * 3 and gs.last_aggressor:
            prof = self.db.get(gs.last_aggressor)
            three_bet_freq = prof.three_bet_freq

            if pf_strength >= 0.85:  # KK, AA → 4-bet
                return Action("raise", gs.our_chips * 0.4,
                              f"4-BET VALUE: {key} vs aggressive 3-bettor")
            elif pf_strength >= 0.65 and three_bet_freq > 0.12:
                # Opponent 3-bets wide → flat call or 4-bet bluff
                return Action("call", gs.call_amount,
                              f"FLAT CALL 3-bet: {key}, opp 3b={three_bet_freq:.0%}")
            elif pf_strength >= 0.78:
                return Action("call", gs.call_amount, f"CALL 3-bet with strong hand: {key}")
            else:
                return Action("fold", 0, f"FOLD to 3-bet: {key} below threshold")

        # Facing a raise (not 3-bet)
        if gs.call_amount > 0:
            if gs.last_aggressor:
                prof = self.db.get(gs.last_aggressor)
                # If opener is tight (NIT/TAG), need stronger hands to call
                adj = 0.05 if prof.classify() in ("NIT", "TAG") else -0.05
            else:
                adj = 0

            call_threshold = 0.50 + adj  # baseline call threshold

            if pf_strength >= 0.80 and should_3bet(gs.hole_cards):
                sz = gs.call_amount * 3
                return Action("raise", sz, f"3-BET: {key}")
            elif pf_strength >= call_threshold:
                return Action("call", gs.call_amount, f"CALL open: {key} strength={pf_strength:.2f}")
            else:
                return Action("fold", 0, f"FOLD vs open: {key}")

        # First to act (limp or raise)
        if raise_open_freq > 0.3:
            # Standard open raise = 2.5x BB
            sz = gs.big_blind * 2.5 + (gs.num_players - 2) * gs.big_blind * 0.5
            return Action("raise", sz, f"OPEN RAISE: {key} from {gs.position}")
        elif raise_open_freq > 0 and gs.position in ("BTN", "SB"):
            # Steal raise
            sz = steal_raise_size(gs.big_blind)
            return Action("raise", sz, f"STEAL: {key} from {gs.position}")
        elif raise_open_freq > 0:
            return Action("call", gs.big_blind, f"LIMP: {key}")
        else:
            return Action("check" if gs.call_amount == 0 else "fold", 0,
                          f"FOLD: {key} below range threshold from {gs.position}")

    # ─── Postflop Decision ────────────────────────────────────────────────────

    def _decide_postflop(self, state: GameState) -> Action:
        gs = state
        num_opps = len(gs.active_opponents)

        # Calculate equity via Monte Carlo
        sims = 800 if gs.street == "flop" else 400
        raw_eq = equity_monte_carlo(
            gs.hole_cards, gs.board,
            num_opponents=num_opps,
            num_simulations=sims
        )

        # v3: Multi-way equity discount
        eq = self._apply_multiway_equity_discount(raw_eq, num_opps)

        odds = pot_odds(gs.call_amount, gs.pot)
        ev = expected_value(eq, gs.pot, gs.call_amount) if gs.call_amount > 0 else 0
        pressure = stack_pressure_factor(gs.our_chips, gs.big_blind)
        risk_thresh = risk_of_ruin_threshold(gs.our_chips, gs.big_blind, self.aggression)

        # v3: SPR calculation
        spr = gs.our_chips / gs.pot if gs.pot > 0 else 99

        # v3: ICM Bubble Factor Guard — chip leaders can't afford 50/50 flips
        is_allin_situation = gs.call_amount >= gs.our_chips * 0.75
        if is_allin_situation and gs.call_amount > 0:
            chip_leader = self._is_chip_leader(gs.our_chips, gs.active_opponents)
            call_threshold = ICM_CHIP_LEADER_CALL_THRESHOLD if chip_leader else odds
            if eq < call_threshold:
                return Action("fold", 0,
                              f"ICM BUBBLE FOLD: eq={eq:.1%} < "
                              f"{'52.2% (chip-leader threshold)' if chip_leader else f'{odds:.1%} (pot odds)'}")
            else:
                return Action("call", gs.call_amount,
                              f"ICM CALL: eq={eq:.1%} >= threshold, EV positive")

        # v3: SPR Commitment — pot committed → go all-in
        if spr <= 5 and self._spr_commitment(spr, eq) and gs.call_amount == 0:
            return Action("raise", gs.our_chips,
                          f"SPR COMMIT: spr={spr:.1f}, eq={eq:.1%} — all-in for max value")

        # Aggregate opponent info for this street
        opp_profiles = [self.db.get(pid) for pid in gs.active_opponents]
        avg_fold_cbet = (
            sum(p.fold_to_cbet for p in opp_profiles) / len(opp_profiles)
            if opp_profiles else 0.45
        )

        # ── Strong equity (top ~35%): bet for value ──
        value_threshold = 0.62 - (0.08 if self.aggression == "aggressive" else 0)
        # In multi-way, tighten value threshold slightly
        if num_opps >= 3:
            value_threshold += 0.05

        if eq >= value_threshold:
            bet_size = self._size_value_bet(gs.pot, gs.street, eq)
            return Action("raise" if gs.call_amount > 0 else "bet",
                          bet_size if gs.call_amount == 0 else bet_size + gs.call_amount,
                          f"VALUE BET: eq={eq:.0%} (raw={raw_eq:.0%}), street={gs.street}")

        # ── Continuation bet window ──
        if gs.street == "flop" and eq >= 0.45 and gs.call_amount == 0:
            # Don't cbet into 3+ opponents without strong equity
            if num_opps >= 3 and eq < 0.60:
                pass  # skip cbet multi-way without strong equity
            elif avg_fold_cbet >= 0.50 or eq >= 0.52:
                cbet_size = gs.pot * 0.55
                self._cbet_count += 1
                return Action("bet", cbet_size,
                              f"CBET: eq={eq:.0%}, opp_fold={avg_fold_cbet:.0%}")

        # ── Bluff / semi-bluff window ── (heads-up or 2-way only)
        if gs.call_amount == 0 and eq >= 0.35 and num_opps <= 2:
            if avg_fold_cbet >= 0.62 and gs.street in ("flop", "turn"):
                bluff_size = gs.pot * 0.65
                return Action("bet", bluff_size,
                              f"BLUFF: opp_fold={avg_fold_cbet:.0%}, eq={eq:.0%}")

        # ── Check-raise opportunity (turn with strong equity) ──
        if gs.street == "turn" and gs.call_amount > 0 and eq >= 0.70:
            raise_size = gs.call_amount * 3 + gs.pot * 0.3
            return Action("raise", raise_size, f"CHECK-RAISE VALUE: eq={eq:.0%}")

        # ── Calling zone: +EV calls ──
        if gs.call_amount > 0 and ev > 0 and eq > odds:
            return Action("call", gs.call_amount,
                          f"EV+ CALL: eq={eq:.0%} vs odds={odds:.0%}, EV={ev:.1f}")

        # ── Bluff catch: opponent profile says they bluff a lot ──
        if gs.call_amount > 0 and gs.last_aggressor:
            bluffer = self.db.get(gs.last_aggressor)
            if bluffer.bluff_frequency > 0.40 and eq >= 0.35:
                return Action("call", gs.call_amount,
                              f"BLUFF CATCH: opp_bluff={bluffer.bluff_frequency:.0%}")

        # ── Check or fold ──
        if gs.call_amount == 0:
            return Action("check", 0, f"CHECK: eq={eq:.0%}, no bet opportunity")
        return Action("fold", 0, f"FOLD: eq={eq:.0%} < odds={odds:.0%}, EV={ev:.1f}")

    # ─── Bet Sizing Logic ──────────────────────────────────────────────────────

    def _size_value_bet(self, pot: float, street: str, equity: float) -> float:
        """
        Optimal value bet sizing by street and equity.
        Strong equity / thin board = larger sizing.
        """
        base_pct = {
            "flop": 0.55,
            "turn": 0.70,
            "river": 0.85,
        }.get(street, 0.65)

        # Scale up for nut-like hands
        if equity >= 0.85:
            base_pct = min(1.2, base_pct * 1.4)  # overbet for max value
        elif equity >= 0.75:
            base_pct *= 1.15

        return round(pot * base_pct, 1)


# ─── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from hand_evaluator import parse_hand

    db = OpponentDatabase()
    engine = DecisionEngine(db, aggression="balanced")

    # Simulate a preflop decision: AA on BTN
    state_pre = GameState(
        hole_cards=parse_hand(["As", "Ah"]),
        board=[],
        pot=150,
        call_amount=100,
        our_chips=2000,
        big_blind=50,
        position="BTN",
        street="preflop",
        num_players=6,
        active_opponents=["Villain1", "Villain2"],
        last_aggressor="Villain1"
    )
    action_pre = engine.decide(state_pre)
    print(f"Preflop AA vs raise: {action_pre.action.upper()} {action_pre.amount}")
    print(f"  → {action_pre.reasoning}")

    # Simulate a flop decision: AKs with top pair
    state_flop = GameState(
        hole_cards=parse_hand(["As", "Ks"]),
        board=parse_hand(["Ah", "7d", "2c"]),
        pot=300,
        call_amount=0,
        our_chips=2000,
        big_blind=50,
        position="BTN",
        street="flop",
        num_players=2,
        active_opponents=["Villain1"],
        last_aggressor=None
    )
    action_flop = engine.decide(state_flop)
    print(f"\nFlop AKs on A72: {action_flop.action.upper()} {action_flop.amount}")
    print(f"  → {action_flop.reasoning}")
