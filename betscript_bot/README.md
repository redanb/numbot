# BetScript Bot v3.1-God-Level
**The "Outsider" Exploitative Decision Engine**

## Overview
BetScript Bot v3.1 is an advanced poker AI designed for competition environments. Unlike traditional GTO bots that attempt to play "unexploitable" poker, BetScript is built on the **First Principles of Exploitative Game Theory**. It prioritizes **vulnerability detection** in opponents and employs a **Dynamic ROIC (Return on Invested Capital)** model to maximize profit while minimizing risk.

## Core Architecture
- **Adaptive Aggression Engine (v3.1):** Features a 20-hand Bayesian "Probe Gate" that observes field tendencies before locking into the optimal exploitation mode (Aggressive, Balanced, or Conservative).
- **ICM Bubble Factor Guard:** Implements verified Malmuth-Harville 3-player ICM math, enforcing a 52.2% equity floor for chip-leader all-in calls.
- **Multi-Way Equity Discounting:** Dynamically adjusts Monte Carlo equity estimates by 8% per additional opponent to prevent over-valuing hands in multi-way pots.
- **SPR-Based Commitment Logic:** Automatically identifies "Pot-Committed" scenarios (SPR < 3) to press edges when the math dictates it.

## Technical Specs
- **Logic:** Hybrid Bayesian + GTO-Approximate logic.
- **Engine:** PyPokerEngine implementation.
- **Dependencies:** None (Pure Python 3.9+ Standard Library).
- **Performance:** Sub-10ms decision time per action.

## Strategic Frameworks
The bot's design incorporates business logic and military strategy:
- **Porter's Five Forces:** Used to analyze table dynamics and "Barrier to Entry" for chips.
- **Sun Tzu’s Art of War:** Employs "The Way of the Farmer" (early accumulation) and "The Way of the Commander" (late-stage pressure).
- **Blue Ocean Strategy:** Targets underserved pots and uses information asymmetry to outmaneuver "standard" bots.

---
*Created by Team BetScript — "You are not just building a bot; you are building a money-printing machine that understands the psychology of its competition."*
