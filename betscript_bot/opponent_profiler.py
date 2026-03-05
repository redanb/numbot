"""
opponent_profiler.py — BetScript Bot
Bayesian opponent modeling: track and exploit player tendencies in real-time.
Profiles are built automatically from observed betting actions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
import math

# ─── Opponent Statistics Container ──────────────────────────────────────────

@dataclass
class PlayerProfile:
    player_id: str

    # VPIP — voluntarily put money in pre-flop
    vpip_hands: int = 0          # hands where they had the option
    vpip_count: int = 0          # times they entered voluntarily

    # PFR — pre-flop raise %
    pfr_hands: int = 0
    pfr_count: int = 0

    # Aggression Factor (AF): (raises+bets) / calls, post-flop
    postflop_raises: int = 0
    postflop_bets: int = 0
    postflop_calls: int = 0

    # Fold to Continuation Bet (FCB)
    cbet_faced: int = 0
    cbet_folded: int = 0

    # 3-bet frequency
    three_bet_opportunities: int = 0
    three_bet_count: int = 0

    # Bluff frequency (hands shown down that were bluffs)
    bluffs_shown: int = 0
    showdowns: int = 0

    # Fold to 3-bet
    three_bet_faced: int = 0
    three_bet_folded: int = 0

    # Bet sizing tells
    bet_sizes: list = field(default_factory=list)  # as % of pot

    # Chip stack trajectory
    chips_history: list = field(default_factory=list)

    # v3: Total hands observed (for 20-hand probe gate check)
    hands_observed: int = 0

    @property
    def vpip(self) -> float:
        """VPIP: % of hands voluntarily entered. Typical: fish=40+%, reg=20-28%."""
        if self.vpip_hands == 0: return 0.25  # prior
        return self.vpip_count / self.vpip_hands

    @property
    def pfr(self) -> float:
        """PFR: % of hands raised preflop."""
        if self.pfr_hands == 0: return 0.15  # prior
        return self.pfr_count / self.pfr_hands

    @property
    def aggression_factor(self) -> float:
        """AF: high = aggressive, low = passive."""
        if self.postflop_calls == 0: return 1.0
        return (self.postflop_raises + self.postflop_bets) / self.postflop_calls

    @property
    def fold_to_cbet(self) -> float:
        """FCB: how often they fold to a continuation bet."""
        if self.cbet_faced == 0: return 0.45  # prior (average player)
        return self.cbet_folded / self.cbet_faced

    @property
    def three_bet_freq(self) -> float:
        """3-bet frequency."""
        if self.three_bet_opportunities == 0: return 0.06  # prior
        return self.three_bet_count / self.three_bet_opportunities

    @property
    def fold_to_3bet(self) -> float:
        """How often they fold to 3-bets."""
        if self.three_bet_faced == 0: return 0.55  # prior
        return self.three_bet_folded / self.three_bet_faced

    @property
    def bluff_frequency(self) -> float:
        """Estimated bluff frequency from showdowns."""
        if self.showdowns < 3: return 0.3  # prior
        return self.bluffs_shown / self.showdowns

    @property
    def avg_bet_size(self) -> float:
        """Average bet as % of pot."""
        if not self.bet_sizes: return 0.65  # prior: 65% pot
        return sum(self.bet_sizes) / len(self.bet_sizes)

    def confidence(self) -> float:
        """Confidence in profile [0–1] based on sample size. Reaches ~95% after 45 hands."""
        n = self.vpip_hands
        return 1 - math.exp(-n / 15)

    @property
    def probe_complete(self) -> bool:
        """True once we've observed 20+ hands (v3: probe gate threshold)."""
        return self.hands_observed >= 20  # approaches 1 after ~45 hands

    def classify(self) -> str:
        """Classify player archetype."""
        v, p = self.vpip, self.pfr
        af = self.aggression_factor
        if v < 0.20 and p >= 0.15: return "TAG"        # Tight-Aggressive (reg)
        if v >= 0.35 and af >= 2.0: return "LAG"        # Loose-Aggressive (maniac)
        if v >= 0.35 and af < 1.5: return "FISH"       # Loose-Passive (calling station)
        if v < 0.20 and af < 1.2: return "NIT"         # Tight-Passive (rock)
        return "REG"                                     # Regular / balanced

    def exploit_action(self) -> Dict[str, str]:
        """
        Return actionable exploits based on profile.
        """
        tips = {}
        ctype = self.classify()

        if ctype == "FISH":
            tips["bluffing"] = "REDUCE — fish call too often; value bet thin instead"
            tips["value_betting"] = "INCREASE thin value bets — fish won't fold medium hands"
        elif ctype == "NIT":
            tips["bluffing"] = "INCREASE — nits fold too much; steal more often"
            tips["value_betting"] = "REDUCE ranges — nits only continue with strong hands"
        elif ctype == "LAG":
            tips["defense"] = "CALL DOWN more — they bluff high frequency"
            tips["3_bet"] = "TIGHTEN only to monsters — they 4-bet bluff light"
        elif ctype == "TAG":
            tips["default"] = "Play solid GTO — minimal exploitation margin"
        
        if self.fold_to_cbet > 0.65:
            tips["cbet"] = f"FIRE continuation bets aggressively ({self.fold_to_cbet:.0%} fold rate)"
        if self.fold_to_3bet > 0.70:
            tips["3bet_bluff"] = f"3-bet bluff more ({self.fold_to_3bet:.0%} fold to 3-bet)"
        if self.fold_to_3bet < 0.40:
            tips["3bet_value"] = "Tighten 3-bet to value only — they fight back"

        return tips

    def __repr__(self):
        c = self.confidence()
        return (
            f"[{self.player_id}] {self.classify()} "
            f"| VPIP={self.vpip:.0%} PFR={self.pfr:.0%} "
            f"AF={self.aggression_factor:.1f} "
            f"F2C={self.fold_to_cbet:.0%} "
            f"3B%={self.three_bet_freq:.0%} "
            f"Conf={c:.0%}"
        )


# ─── Profile Registry ─────────────────────────────────────────────────────────

class OpponentDatabase:
    """Session-scoped registry of all opponent profiles."""

    def __init__(self):
        self._profiles: Dict[str, PlayerProfile] = {}

    def get(self, player_id: str) -> PlayerProfile:
        if player_id not in self._profiles:
            self._profiles[player_id] = PlayerProfile(player_id=player_id)
        return self._profiles[player_id]

    def all_players(self):
        return list(self._profiles.values())

    # ─── Event Handlers ───────────────────────────────────────────────────────

    def record_preflop_action(self, player_id: str, action: str, facing_raise: bool):
        """Call on every preflop action we observe."""
        p = self.get(player_id)
        p.hands_observed += 1   # v3: increment probe counter
        p.vpip_hands += 1
        p.pfr_hands += 1

        if action in ("call", "raise", "bet"):
            p.vpip_count += 1
        if action == "raise":
            p.pfr_count += 1

        if facing_raise and action in ("raise",):
            p.three_bet_count += 1
        if facing_raise:
            p.three_bet_opportunities += 1

    def record_fold_to_3bet(self, player_id: str, folded: bool):
        p = self.get(player_id)
        p.three_bet_faced += 1
        if folded:
            p.three_bet_folded += 1

    def record_postflop_action(self, player_id: str, action: str, bet_size_pct: float = None):
        """Call on every postflop action we observe."""
        p = self.get(player_id)
        if action in ("raise", "reraise"):
            p.postflop_raises += 1
        elif action == "bet":
            p.postflop_bets += 1
            if bet_size_pct is not None:
                p.bet_sizes.append(bet_size_pct)
        elif action == "call":
            p.postflop_calls += 1

    def record_cbet_response(self, player_id: str, folded: bool):
        """Call when opponent faces a continuation bet."""
        p = self.get(player_id)
        p.cbet_faced += 1
        if folded:
            p.cbet_folded += 1

    def record_showdown(self, player_id: str, was_bluff: bool):
        p = self.get(player_id)
        p.showdowns += 1
        if was_bluff:
            p.bluffs_shown += 1

    def record_chips(self, player_id: str, chips: float):
        p = self.get(player_id)
        p.chips_history.append(chips)

    def weakest_player(self) -> Optional[str]:
        """
        Return player_id of most exploitable opponent.
        Prioritizes high VPIP (fish) or high fold_to_cbet (nitty).
        """
        best = None
        best_score = -1
        for p in self._profiles.values():
            # Exploit score: high VPIP + low AF = calling station
            exploit_score = p.vpip * 2 - p.aggression_factor * 0.5
            if exploit_score > best_score:
                best_score = exploit_score
                best = p.player_id
        return best

    def most_aggressive(self) -> Optional[str]:
        """Return player_id with highest aggression factor."""
        players = list(self._profiles.values())
        if not players: return None
        return max(players, key=lambda p: p.aggression_factor).player_id

    def print_all(self):
        for p in self._profiles.values():
            print(p)
            tips = p.exploit_action()
            for k, v in tips.items():
                print(f"  → [{k.upper()}]: {v}")
            print()


# ─── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    db = OpponentDatabase()

    # Simulate 20 hands against "PlayerA" (fish-like)
    for i in range(20):
        db.record_preflop_action("PlayerA", "call", facing_raise=False)
        db.record_postflop_action("PlayerA", "call")
        if i % 3 == 0:
            db.record_cbet_response("PlayerA", folded=False)  # calls cbet
        else:
            db.record_cbet_response("PlayerA", folded=True)

    # Simulate 15 hands against "PlayerB" (nit-like)
    for i in range(15):
        db.record_preflop_action("PlayerB", "fold", facing_raise=True)
        if i % 5 == 0:
            db.record_postflop_action("PlayerB", "raise")
        else:
            db.record_postflop_action("PlayerB", "call")
        db.record_cbet_response("PlayerB", folded=True)

    print("=== Opponent Profiles ===")
    db.print_all()
    print(f"Weakest player: {db.weakest_player()}")
    print(f"Most aggressive: {db.most_aggressive()}")
