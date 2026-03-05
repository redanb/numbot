"""
BetScript God-Level Poker Bot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Hybrid GTO + Bayesian Exploitative Architecture
"""

from .hand_evaluator import equity_monte_carlo, preflop_hand_strength, card_from_str
from .opponent_profiler import OpponentDatabase
from .decision_engine import DecisionEngine, GameState, Action
from .bot import BetScriptBot
from .range_tables import hand_key, should_open_raise
from .tournament_pressure import stack_pressure_factor

__version__ = "1.0.0"
__author__ = "BetScript Team"

__all__ = [
    "BetScriptBot",
    "DecisionEngine",
    "GameState",
    "Action",
    "OpponentDatabase",
    "equity_monte_carlo",
    "preflop_hand_strength",
    "hand_key",
    "should_open_raise",
    "stack_pressure_factor",
]
