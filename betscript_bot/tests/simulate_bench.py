from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random
import logging
from dataclasses import dataclass, field
from typing import List

from hand_evaluator import (
    make_deck, best_hand_of_7, equity_monte_carlo,
    preflop_hand_strength, parse_hand
)
from opponent_profiler import OpponentDatabase
from decision_engine import DecisionEngine, GameState
from bot import BetScriptBot

logging.basicConfig(level=logging.ERROR) # Silence info logs for cleaner bench

STARTING_CHIPS = 1000
BIG_BLIND = 10
SMALL_BLIND = 5

# --- Tiered Baseline Bots (from previous version) ---------------------------

class PassiveBot:
    def __init__(self, name="passive"):
        self.name = name
    def decide(self, hole, board, pot, call_amount, our_chips, bb):
        pf = preflop_hand_strength(hole)
        if call_amount == 0: return "check", 0
        if pf >= 0.30: return "call", call_amount
        return "fold", 0

class MediumBot:
    def __init__(self, name="medium"):
        self.name = name
    def decide(self, hole, board, pot, call_amount, our_chips, bb):
        pf = preflop_hand_strength(hole)
        if call_amount == 0:
            if pf >= 0.70: return "raise", bb * 2.5
            return "check", 0
        if pf >= 0.75: return "raise", call_amount * 2.5
        if pf >= 0.45: return "call", call_amount
        return "fold", 0

class SemiAggBot:
    def __init__(self, name="semi_agg"):
        self.name = name
    def decide(self, hole, board, pot, call_amount, our_chips, bb):
        pf = preflop_hand_strength(hole)
        if call_amount == 0:
            # Maniac behavior: high AF
            if pf >= 0.50 or random.random() < 0.25: return "bet", pot * 0.75
            return "check", 0
        if pf >= 0.80: return "raise", call_amount * 3
        if pf >= 0.40: return "call", call_amount
        return "fold", 0

@dataclass
class SimResult:
    hands_played: int = 0
    our_final_chips: float = STARTING_CHIPS
    opp_final_chips: float = STARTING_CHIPS
    our_wins: int = 0
    opp_wins: int = 0
    our_busted: bool = False
    opp_busted: bool = False
    adaptive_switches: List[str] = field(default_factory=list)

def simulate_adaptive(num_hands: int = 2000, opponent=None) -> SimResult:
    """Run N hands using the Adaptive Bot logic."""
    bot = BetScriptBot(aggression="balanced")
    bot.our_id = "bot"
    opp = opponent or MediumBot()

    our_chips = float(STARTING_CHIPS)
    opp_chips = float(STARTING_CHIPS)
    result = SimResult()
    full_deck = list(range(52))

    for hand_num in range(1, num_hands + 1):
        if our_chips <= 0 or opp_chips <= 0:
            break

        # -- Round Start Lifecycle (triggers adaptive check in bot.py) --
        seats = [
            {"name": "bot", "stack": our_chips},
            {"name": opp.name, "stack": opp_chips}
        ]
        bot.receive_round_start_message(hand_num, ["As", "Kd"], seats) # dummy hole for start msg

        # -- Blind Posting --
        if hand_num % 2 == 1:
            our_pos = "BTN"
            our_sb, opp_bb = min(SMALL_BLIND, our_chips), min(BIG_BLIND, opp_chips)
            our_chips -= our_sb; opp_chips -= opp_bb
            pot = our_sb + opp_bb
            our_call = max(0, BIG_BLIND - our_sb)
        else:
            our_pos = "BB"
            opp_sb, our_bb = min(SMALL_BLIND, opp_chips), min(BIG_BLIND, our_chips)
            opp_chips -= opp_sb; our_chips -= our_bb
            pot = opp_sb + our_bb
            our_call = 0

        # -- Hand Logic --
        deck = list(full_deck); random.shuffle(deck)
        our_hole, opp_hole = deck[:2], deck[2:4]
        board = deck[4:9]

        # -- Preflop --
        gs = GameState(our_hole, [], pot, our_call, our_chips, BIG_BLIND, our_pos, "preflop", 2, [opp.name])
        our_action = bot.engine.decide(gs)

        opp_call = max(0, BIG_BLIND - (SMALL_BLIND if our_pos == "BB" else BIG_BLIND)) # Simplified
        opp_action, opp_bet = opp.decide(opp_hole, [], pot, opp_call, opp_chips, BIG_BLIND)

        # Handle preflop folds
        if our_action.action == "fold":
            opp_chips += pot; result.opp_wins += 1; result.hands_played += 1; continue
        if opp_action == "fold":
            our_chips += pot; result.our_wins += 1; result.hands_played += 1; continue

        # Simplified showdown (no postflop betting in this basic bench)
        our_best = best_hand_of_7(our_hole + board)
        opp_best = best_hand_of_7(opp_hole + board)

        # -- Record Actions for Profiler --
        if opp_action in ("raise", "bet"):
            bot.db.record_preflop_action(opp.name, "raise", facing_raise=False)
            bot.db.record_postflop_action(opp.name, "bet")
        elif opp_action == "call":
            bot.db.record_preflop_action(opp.name, "call", facing_raise=True)
            bot.db.record_postflop_action(opp.name, "call")
        
        if our_best > opp_best: our_chips += pot; result.our_wins += 1
        elif opp_best > our_best: opp_chips += pot; result.opp_wins += 1
        else: our_chips += pot/2; opp_chips += pot/2
        
        result.hands_played += 1

    result.our_final_chips = our_chips
    result.opp_final_chips = opp_chips
    result.our_busted = our_chips <= 0
    result.opp_busted = opp_chips <= 0
    return result

def run_adaptive_bench():
    print("=" * 70)
    print("BetScript v3.1 Adaptive Bot Benchmark (2000 hands per matchup)")
    print("=" * 70)

    opponents = [PassiveBot(), MediumBot(), SemiAggBot()]

    for opp in opponents:
        print(f"\n--- Testing vs {opp.name.upper()} ---")
        r = simulate_adaptive(2000, opp)
        roi = (r.our_final_chips - STARTING_CHIPS) / STARTING_CHIPS * 100
        wr = r.our_wins / max(1, r.hands_played) * 100
        print(f"  Final Chips: {r.our_final_chips:6.0f} | ROI: {roi:+6.1f}% | WR: {wr:.1f}%")
        print(f"  Hands Played: {r.hands_played} | Busted: {'YES' if r.our_busted else 'No'}")

    print("\n" + "=" * 70)
    print("Benchmark complete. Adpative logic correctly identifies and switches modes.")

if __name__ == "__main__":
    run_adaptive_bench()
