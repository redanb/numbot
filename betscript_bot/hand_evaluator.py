"""
hand_evaluator.py — BetScript Bot
Monte Carlo hand strength calculator + equity estimator.
Uses standard 52-card deck with fast combinatoric evaluation.
"""

from __future__ import annotations
import random
import itertools
from functools import lru_cache
from typing import List, Tuple, Optional

# ─── Card Representation ────────────────────────────────────────────────────
# Card = int  (0-51)  where card = rank*4 + suit
# Rank: 0=2, 1=3, ..., 8=T, 9=J, 10=Q, 11=K, 12=A
# Suit: 0=c, 1=d, 2=h, 3=s

RANKS = "23456789TJQKA"
SUITS = "cdhs"

def card_from_str(s: str) -> int:
    """Parse '2c', 'Ah', 'Td' etc → int."""
    rank = RANKS.index(s[0].upper() if s[0].upper() in RANKS else s[0])
    suit = SUITS.index(s[1].lower())
    return rank * 4 + suit

def card_to_str(c: int) -> str:
    return RANKS[c // 4] + SUITS[c % 4]

def make_deck(exclude: List[int] = None) -> List[int]:
    exclude = set(exclude or [])
    return [c for c in range(52) if c not in exclude]

def parse_hand(cards: List[str]) -> List[int]:
    return [card_from_str(c) for c in cards]

# ─── 5-Card Hand Evaluator ───────────────────────────────────────────────────
# Returns a tuple usable for comparison (higher = better hand)
# Based on the classic rank-category system

def rank_of(c: int) -> int: return c // 4
def suit_of(c: int) -> int: return c % 4

def _hand_rank_5(cards: Tuple[int, ...]) -> Tuple:
    """Evaluate exactly 5 cards. Returns comparable tuple (higher = better)."""
    ranks = sorted([rank_of(c) for c in cards], reverse=True)
    suits = [suit_of(c) for c in cards]
    flush = len(set(suits)) == 1
    straight = (ranks[0] - ranks[4] == 4 and len(set(ranks)) == 5)
    # Wheel straight: A-2-3-4-5
    if set(ranks) == {12, 0, 1, 2, 3}:
        straight = True
        ranks = [3, 2, 1, 0, -1]  # treat Ace as low

    from collections import Counter
    cnt = Counter(ranks)
    groups = sorted(cnt.items(), key=lambda x: (x[1], x[0]), reverse=True)
    group_sizes = [g[1] for g in groups]
    group_ranks = [g[0] for g in groups]

    if straight and flush:
        return (8, ranks[0])
    if group_sizes[0] == 4:
        return (7, group_ranks[0], group_ranks[1])
    if group_sizes[:2] == [3, 2]:
        return (6, group_ranks[0], group_ranks[1])
    if flush:
        return (5,) + tuple(ranks)
    if straight:
        return (4, ranks[0])
    if group_sizes[0] == 3:
        return (3, group_ranks[0]) + tuple(group_ranks[1:])
    if group_sizes[:2] == [2, 2]:
        return (2, max(group_ranks[:2]), min(group_ranks[:2]), group_ranks[2])
    if group_sizes[0] == 2:
        return (1, group_ranks[0]) + tuple(group_ranks[1:])
    return (0,) + tuple(ranks)

def best_hand_of_7(cards: List[int]) -> Tuple:
    """Find best 5-card hand from up to 7 cards."""
    best = None
    for combo in itertools.combinations(cards, 5):
        rank = _hand_rank_5(combo)
        if best is None or rank > best:
            best = rank
    return best  # type: ignore

def compare_hands(hole: List[int], opponent_hole: List[int], board: List[int]) -> int:
    """Return 1 if hole wins, -1 if opponent wins, 0 if tie."""
    h1 = best_hand_of_7(hole + board)
    h2 = best_hand_of_7(opponent_hole + board)
    if h1 > h2: return 1
    if h1 < h2: return -1
    return 0

# ─── Monte Carlo Equity Calculator ──────────────────────────────────────────

def equity_monte_carlo(
    hole: List[int],
    board: List[int],
    num_opponents: int = 1,
    num_simulations: int = 1000,
) -> float:
    """
    Estimate win equity for our hole cards via Monte Carlo.
    Returns win probability [0.0, 1.0].
    """
    known = set(hole + board)
    deck = make_deck(exclude=list(known))

    wins = 0
    ties = 0
    total = 0

    for _ in range(num_simulations):
        remaining_board = 5 - len(board)
        if remaining_board < 0:
            break

        sample = random.sample(deck, remaining_board + num_opponents * 2)
        run_board = board + sample[:remaining_board]
        opp_start = remaining_board

        our_rank = best_hand_of_7(hole + run_board)
        best_opp = None
        for i in range(num_opponents):
            opp_hole = sample[opp_start + i*2 : opp_start + i*2 + 2]
            opp_rank = best_hand_of_7(opp_hole + run_board)
            if best_opp is None or opp_rank > best_opp:
                best_opp = opp_rank

        if our_rank > best_opp:
            wins += 1
        elif our_rank == best_opp:
            ties += 1
        total += 1

    if total == 0:
        return 0.5
    return (wins + 0.5 * ties) / total

# ─── Pre-flop Hand Strength (Static) ─────────────────────────────────────────

def preflop_hand_strength(hole: List[int]) -> float:
    """
    Fast static preflop strength score [0.0–1.0] based on Sklansky groups.
    """
    r1, r2 = sorted([rank_of(c) for c in hole], reverse=True)
    suited = suit_of(hole[0]) == suit_of(hole[1])
    paired = r1 == r2

    # Premium pairs
    if paired and r1 >= 10:  # TT, JJ, QQ, KK, AA
        return 0.85 + (r1 - 10) * 0.03  # AA=0.97
    # Medium pairs
    if paired and r1 >= 6:
        return 0.65 + (r1 - 6) * 0.025
    # Small pairs
    if paired:
        return 0.50

    # Ace high
    if r1 == 12:  # Ace
        kicker_score = r2 / 12.0
        return 0.55 + kicker_score * 0.25 + (0.05 if suited else 0)

    # Connected suited (e.g., JTs)
    gap = r1 - r2
    base = (r1 + r2) / 24.0  # normalize
    suited_bonus = 0.08 if suited else 0
    connected_bonus = max(0, (3 - gap) * 0.03)

    return min(0.82, base * 0.6 + suited_bonus + connected_bonus + 0.1)

# ─── Pot Odds & EV Calculation ───────────────────────────────────────────────

def pot_odds(call_amount: float, pot_size: float) -> float:
    """Return required equity to profitably call."""
    if call_amount <= 0:
        return 0.0
    return call_amount / (pot_size + call_amount)

def expected_value(equity: float, pot: float, call_amount: float) -> float:
    """EV of calling: positive means call is profitable."""
    return equity * (pot + call_amount) - (1 - equity) * call_amount


# ─── Quick test ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    hole = parse_hand(["As", "Kh"])
    board = parse_hand(["Qd", "Jc", "2s"])
    eq = equity_monte_carlo(hole, board, num_opponents=2, num_simulations=2000)
    pf = preflop_hand_strength(hole)
    odds = pot_odds(50, 200)
    ev = expected_value(eq, 200, 50)
    print(f"Hole: As Kh | Board: Qd Jc 2s")
    print(f"Equity vs 2 opponents: {eq:.2%}")
    print(f"Preflop strength:       {pf:.2%}")
    print(f"Pot odds (50 into 200): {odds:.2%}")
    print(f"EV of call:             {ev:.2f} chips")
