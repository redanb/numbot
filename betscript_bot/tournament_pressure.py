"""
tournament_pressure.py — BetScript Bot
Chip-survival pressure logic and tournament-adjusted strategy.
Implements ICM-aware concepts: chip EV vs tournament EV divergence.
"""

from __future__ import annotations
from typing import List, Dict
import math

# ─── Stack-to-Blinds Pressure ─────────────────────────────────────────────────

def stack_pressure_factor(chips: float, big_blind: float) -> float:
    """
    Returns a pressure multiplier [0.0–1.0].
    High pressure = fewer chips relative to blinds → must act more desperately.
    Low pressure = deep stack → can afford to be selective.

    M-ratio: chips / (SB + BB) = effective rounds before blinding out
    """
    if big_blind <= 0:
        return 0.0
    m_ratio = chips / (big_blind * 1.5)  # 1 BB + 0.5 SB
    
    # Green zone: M > 20 → comfortable, play normally
    # Yellow zone: 10 < M <= 20 → tighten a bit
    # Orange zone: 5 < M <= 10 → push/fold mode approaching
    # Red zone: M <= 5 → pure push/fold
    if m_ratio > 20:
        return 0.0   # no pressure
    elif m_ratio > 10:
        return (20 - m_ratio) / 20 * 0.3  # mild pressure
    elif m_ratio > 5:
        return 0.3 + (10 - m_ratio) / 10 * 0.4  # significant
    else:
        return min(1.0, 0.7 + (5 - m_ratio) / 10)  # near desperation

def recommended_open_sizing(base_chips: float, pot: float, pressure: float) -> float:
    """
    Return recommended open-raise size.
    Under pressure: shove more, raise to commit.
    Deep stack: standard 2.5-3x opens.
    """
    # Baseline: 2.5x big blind (or 3x if single open)
    # Adjust down under heavy pressure toward shove-or-fold
    if pressure >= 0.7:
        return base_chips  # shove
    elif pressure >= 0.4:
        multiplier = 2.0
    else:
        multiplier = 2.5 + (1 - pressure) * 0.5  # up to 3.0x

    return round(pot * multiplier, 1)

# ─── Push/Fold Ranges (Nash Equilibrium Approximate) ──────────────────────────
# M <= 10: use these simplified Nash push ranges by position
# Source: simplified from Nash ICM push/fold charts (10BB effective stacks)

def should_push_allin(hand_strength: float, chips: float, big_blind: float, position: str) -> bool:
    """
    Decide whether to go all-in (push) preflop given short stack.
    Uses hand_strength from hand_evaluator.preflop_hand_strength().
    """
    m = chips / (big_blind * 1.5)
    if m > 15:
        return False  # deep stack, don't push light

    # Threshold by position and stack depth
    # BTN/SB push widest, UTG pushes tighter
    thresholds: Dict[str, List] = {
        "UTG": [0.75, 0.65, 0.55, 0.45],  # M=10, 7, 5, 3
        "MP":  [0.70, 0.60, 0.50, 0.40],
        "CO":  [0.65, 0.55, 0.45, 0.35],
        "BTN": [0.55, 0.45, 0.38, 0.28],
        "SB":  [0.50, 0.40, 0.32, 0.22],
    }
    pos_thresholds = thresholds.get(position, thresholds["MP"])

    if m >= 10:   idx = 0
    elif m >= 7:  idx = 1
    elif m >= 5:  idx = 2
    else:         idx = 3

    return hand_strength >= pos_thresholds[idx]

# ─── ICM-Inspired Prize Pool Pressure ─────────────────────────────────────────
# In chip-accumulation competitions, survival matters more near bubble.
# We simulate a simplified ICM adjustment.

def icm_adjusted_equity(
    stack: float,
    all_stacks: List[float],
    prize_structure: List[float] = None,
) -> float:
    """
    Estimate ICM equity (share of prize pool) given stack sizes.
    Simplified: proportional model for quick in-game decisions.
    prize_structure = [0.50, 0.30, 0.20] for top-3 payouts.
    """
    if not prize_structure:
        prize_structure = [1.0]  # winner take all simplification

    total = sum(all_stacks)
    if total == 0:
        return 1.0 / len(all_stacks)

    # Chip Chop approximation (fast, good enough in-game)
    return stack / total * sum(prize_structure)

def risk_of_ruin_threshold(
    stack: float,
    big_blind: float,
    aggression_mode: str = "balanced"
) -> float:
    """
    Minimum equity needed to take a high-variance spot.
    Conservative at short stack (protect chips), aggressive when deep.
    """
    m = stack / (big_blind * 1.5)
    base_threshold = 0.50  # break-even

    # Risk tolerance by mode
    risk_tolerance = {
        "conservative": 0.08,   # need 8% edge to take risks
        "balanced": 0.04,
        "aggressive": 0.01,
    }.get(aggression_mode, 0.04)

    # At low M, be more conservative to survive
    stack_adj = max(0, (10 - m) / 10 * 0.05)

    return base_threshold + risk_tolerance - stack_adj

# ─── Late Position Steal Sizing ───────────────────────────────────────────────

def steal_raise_size(big_blind: float, num_callers: int = 0) -> float:
    """Standard steal sizes from BTN/SB."""
    base = 2.5 * big_blind
    per_caller = 1.0 * big_blind
    return base + per_caller * num_callers


# ─── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    chips = 800
    bb = 100
    pressure = stack_pressure_factor(chips, bb)
    print(f"Chips: {chips}, BB: {bb}")
    print(f"M-ratio: {chips / (bb * 1.5):.1f}")
    print(f"Pressure factor: {pressure:.2f}")
    print(f"Should push (BTN, strength=0.50): {should_push_allin(0.50, chips, bb, 'BTN')}")
    print(f"Steal raise from BTN: {steal_raise_size(bb)}")

    all_stacks = [1800, 1200, 800, 600, 400]
    icm = icm_adjusted_equity(800, all_stacks, [0.5, 0.3, 0.2])
    print(f"ICM equity: {icm:.2%}")
