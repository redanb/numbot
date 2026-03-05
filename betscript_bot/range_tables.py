"""
range_tables.py — BetScript Bot
GTO preflop opening ranges and 3-bet/4-bet ranges by position.
Based on solver-derived ranges commonly used in modern poker theory.

Position index: 0=UTG, 1=MP, 2=CO, 3=BTN, 4=SB, 5=BB
"""

from __future__ import annotations
from typing import Set
from hand_evaluator import RANKS, rank_of, suit_of

# ─── Canonical Hand Key ──────────────────────────────────────────────────────

def hand_key(hole: list) -> str:
    """
    Convert hole cards to canonical key like 'AKs', 'TT', '87o'.
    """
    r1, r2 = rank_of(hole[0]), rank_of(hole[1])
    if r1 < r2:
        r1, r2 = r2, r1
    suited = suit_of(hole[0]) == suit_of(hole[1])
    if r1 == r2:
        return RANKS[r1] + RANKS[r2]
    return RANKS[r1] + RANKS[r2] + ("s" if suited else "o")

# ─── Preflop Ranges (% of time to open-raise) ───────────────────────────────
# Values represent VPIP (voluntarily put in pot) probability [0.0–1.0]
# Ranges sourced from standard GTO preflop solutions (9-handed NL Hold'em)

# 6-max position open-raise frequencies:
OPEN_RAISE_RANGE: dict[str, dict[str, float]] = {
    "UTG": {
        # Premiums: always raise
        "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0,
        "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0,
        "AKo": 1.0, "AQo": 1.0,
        # Strong hands
        "99": 1.0, "88": 0.9, "77": 0.7,
        "KQs": 1.0, "KJs": 1.0, "KTs": 0.9,
        "QJs": 1.0, "QTs": 0.9, "JTs": 1.0,
        "AJo": 0.8, "ATo": 0.5, "KQo": 0.7,
    },
    "MP": {
        "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0,
        "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0, "A9s": 0.6,
        "AKo": 1.0, "AQo": 1.0, "AJo": 0.9,
        "88": 1.0, "77": 0.9, "66": 0.6,
        "KQs": 1.0, "KJs": 1.0, "KTs": 1.0, "K9s": 0.5,
        "QJs": 1.0, "QTs": 1.0, "JTs": 1.0, "T9s": 0.7,
        "KQo": 0.9, "ATo": 0.7,
    },
    "CO": {
        "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0,
        "88": 1.0, "77": 1.0, "66": 0.9, "55": 0.6,
        "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0, "A9s": 0.9, "A8s": 0.7,
        "AKo": 1.0, "AQo": 1.0, "AJo": 1.0, "ATo": 0.9,
        "KQs": 1.0, "KJs": 1.0, "KTs": 1.0, "K9s": 0.8,
        "QJs": 1.0, "QTs": 1.0, "JTs": 1.0, "T9s": 0.9, "98s": 0.7,
        "KQo": 1.0, "KJo": 0.7, "QJo": 0.5,
    },
    "BTN": {
        # BTN can open ~50-55% of hands
        "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0,
        "88": 1.0, "77": 1.0, "66": 1.0, "55": 1.0, "44": 0.9, "33": 0.8, "22": 0.7,
        "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0, "A9s": 1.0,
        "A8s": 1.0, "A7s": 0.9, "A6s": 0.9, "A5s": 1.0, "A4s": 0.9, "A3s": 0.8, "A2s": 0.7,
        "AKo": 1.0, "AQo": 1.0, "AJo": 1.0, "ATo": 1.0, "A9o": 0.7, "A8o": 0.5,
        "KQs": 1.0, "KJs": 1.0, "KTs": 1.0, "K9s": 1.0, "K8s": 0.7, "K7s": 0.6,
        "KQo": 1.0, "KJo": 0.9, "KTo": 0.7,
        "QJs": 1.0, "QTs": 1.0, "Q9s": 0.8,
        "JTs": 1.0, "J9s": 0.8, "T9s": 1.0, "T8s": 0.7,
        "98s": 0.9, "87s": 0.8, "76s": 0.7, "65s": 0.6,
    },
    "SB": {
        # SB vs no action: raise wide, similar to BTN but slightly tighter
        "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0, "99": 1.0,
        "88": 1.0, "77": 1.0, "66": 0.9, "55": 0.8, "44": 0.7,
        "AKs": 1.0, "AQs": 1.0, "AJs": 1.0, "ATs": 1.0, "A9s": 1.0, "A8s": 0.9,
        "AKo": 1.0, "AQo": 1.0, "AJo": 1.0, "ATo": 0.9,
        "KQs": 1.0, "KJs": 1.0, "KTs": 1.0, "K9s": 0.8,
        "QJs": 1.0, "QTs": 1.0, "JTs": 1.0, "T9s": 0.9, "98s": 0.8,
        "KQo": 0.9, "KJo": 0.7,
    },
}

# ─── 3-Bet Ranges (vs open raise) ────────────────────────────────────────────
# Keys = hands that should 3-bet (always or as part of mixed strategy)

THREE_BET_RANGE: dict[str, float] = {
    # Value 3-bets
    "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 0.9, "TT": 0.6,
    "AKs": 1.0, "AQs": 0.8, "AKo": 1.0,
    # Bluff 3-bets (blockers, fold equity)
    "A5s": 0.5, "A4s": 0.5, "A3s": 0.4, "A2s": 0.4,
    "KQs": 0.5, "QJs": 0.3, "JTs": 0.2,
}

# ─── Range Query Helpers ─────────────────────────────────────────────────────

def should_open_raise(hole: list, position: str, random_val: float = None) -> bool:
    """Decide whether to open-raise from given position."""
    import random as _random
    if random_val is None:
        random_val = _random.random()
    key = hand_key(hole)
    pos_range = OPEN_RAISE_RANGE.get(position, OPEN_RAISE_RANGE["MP"])
    freq = pos_range.get(key, 0.0)
    return random_val < freq

def should_3bet(hole: list, random_val: float = None) -> bool:
    """Decide whether to 3-bet."""
    import random as _random
    if random_val is None:
        random_val = _random.random()
    key = hand_key(hole)
    freq = THREE_BET_RANGE.get(key, 0.0)
    return random_val < freq

def open_raise_frequency(hole: list, position: str) -> float:
    """Return raw open-raise frequency for planning."""
    key = hand_key(hole)
    pos_range = OPEN_RAISE_RANGE.get(position, OPEN_RAISE_RANGE["MP"])
    return pos_range.get(key, 0.0)

def position_label(seat: int, num_players: int) -> str:
    """Map seat number to position string."""
    # seat 0 = dealer/BTN, increases counterclockwise
    if num_players <= 2:
        return "BTN" if seat == 0 else "BB"
    if num_players <= 4:
        labels = ["BTN", "SB", "BB", "CO"][:num_players]
    else:
        positions = ["BTN", "SB", "BB", "UTG", "MP", "CO"]
        labels = positions[:num_players]
    return labels[seat % len(labels)]


if __name__ == "__main__":
    from hand_evaluator import parse_hand
    hole = parse_hand(["As", "Ks"])
    print(f"AKs hand key: {hand_key(hole)}")
    print(f"Should open UTG: {should_open_raise(hole, 'UTG')}")
    print(f"Should open BTN: {should_open_raise(hole, 'BTN')}")
    print(f"Should 3-bet: {should_3bet(hole)}")
