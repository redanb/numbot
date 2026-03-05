"""
verify_task.py - BetScript v3 Upgrade Verification
Pass criteria: exit code = 0, all assertions green.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from decision_engine import (
    DecisionEngine, GameState,
    ICM_CHIP_LEADER_CALL_THRESHOLD, ICM_BUBBLE_FACTOR, PROBE_HANDS_REQUIRED
)
from opponent_profiler import OpponentDatabase
from hand_evaluator import parse_hand

results = []

def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    results.append((name, cond, detail))
    suffix = " -- " + detail if detail else ""
    print("  [" + status + "] " + name + suffix)


print("=" * 65)
print("BetScript v3 Verification Suite")
print("=" * 65)

# ============================================================
# BLOCK 1: ICM Constants
# ============================================================
print("\n[1] ICM Constants")
check("ICM threshold = 0.522",
      abs(ICM_CHIP_LEADER_CALL_THRESHOLD - 0.522) < 0.001,
      "got " + str(ICM_CHIP_LEADER_CALL_THRESHOLD))
check("Bubble Factor = 1.092",
      abs(ICM_BUBBLE_FACTOR - 1.092) < 0.001,
      "got " + str(ICM_BUBBLE_FACTOR))
check("Probe threshold = 20", PROBE_HANDS_REQUIRED == 20)

# ============================================================
# BLOCK 2: 20-hand Probe Gate
# ============================================================
print("\n[2] 20-Hand Probe Gate")
db_p = OpponentDatabase()
engine_p = DecisionEngine(db_p)
base = GameState(
    hole_cards=parse_hand(["2c", "7d"]), board=[],
    pot=150, call_amount=100, our_chips=2000, big_blind=50,
    position="MP", street="preflop", num_players=6,
    active_opponents=["V1"], last_aggressor="V1"
)
probe_folds = sum(
    1 for _ in range(20)
    if "PROBE" in engine_p.decide(base).reasoning
)
check("Probe fires for trash (>=15/20 folds)", probe_folds >= 15,
      str(probe_folds) + "/20")

engine_p._hands_decided = 20  # skip past probe gate
strong = GameState(
    hole_cards=parse_hand(["As", "Ah"]), board=[],
    pot=150, call_amount=0, our_chips=2000, big_blind=50,
    position="BTN", street="preflop", num_players=6,
    active_opponents=["V1"]
)
a_strong = engine_p.decide(strong)
check("Post-probe: AA raises (not PROBE fold)",
      a_strong.action == "raise",
      a_strong.action + ": " + a_strong.reasoning[:50])

# ============================================================
# BLOCK 3: ICM Bubble Factor Guard
# ============================================================
print("\n[3] ICM Bubble Factor Guard")
db_icm = OpponentDatabase()
db_icm.get("V1").chips_history.append(500)
e_icm = DecisionEngine(db_icm)
e_icm._hands_decided = 100

# Marginal: 87o on KQJ2 board - we have a gutshot, low equity
marginal = GameState(
    hole_cards=parse_hand(["8h", "7s"]),
    board=parse_hand(["Kd", "Qc", "Jh", "2s"]),
    pot=200, call_amount=1600, our_chips=2000,
    big_blind=50, position="BTN", street="turn",
    num_players=3, active_opponents=["V1"], last_aggressor="V1"
)
a_icm = e_icm.decide(marginal)
check("Chip leader folds marginal all-in (<52.2%)",
      a_icm.action == "fold",
      a_icm.action + ": " + a_icm.reasoning[:60])

# Strong: AK on AK-27 board - two pair, should call
strong_allin = GameState(
    hole_cards=parse_hand(["As", "Kd"]),
    board=parse_hand(["Ah", "Ks", "2c", "7h"]),
    pot=400, call_amount=1600, our_chips=2000,
    big_blind=50, position="BTN", street="turn",
    num_players=2, active_opponents=["V1"], last_aggressor="V1"
)
a_str = e_icm.decide(strong_allin)
check("Chip leader CALLS two-pair all-in (>52.2%)",
      a_str.action == "call",
      a_str.action + ": " + a_str.reasoning[:60])

# ============================================================
# BLOCK 4: Multi-way equity discount
# ============================================================
print("\n[4] Multi-way Equity Discount")
raw = 0.70
discounted = e_icm._apply_multiway_equity_discount(raw, 3)
expected = raw * (1.0 - 0.08 * 2)
check("0.70 with 3 opps -> 0.588",
      abs(discounted - expected) < 0.001,
      "got " + str(round(discounted, 3)))
nd = e_icm._apply_multiway_equity_discount(0.80, 1)
check("1 opponent: no discount applied",
      abs(nd - 0.80) < 0.001,
      "got " + str(round(nd, 3)))

# ============================================================
# BLOCK 5: SPR Commitment
# ============================================================
print("\n[5] SPR Commitment Logic")
check("SPR=2, eq=0.50 -> commit",   e_icm._spr_commitment(2, 0.50) is True)
check("SPR=2, eq=0.30 -> no commit",e_icm._spr_commitment(2, 0.30) is False)
check("SPR=4, eq=0.60 -> commit",   e_icm._spr_commitment(4, 0.60) is True)
check("SPR=9, eq=0.60 -> no commit",e_icm._spr_commitment(9, 0.60) is False)
check("SPR=9, eq=0.80 -> commit",   e_icm._spr_commitment(9, 0.80) is True)

# ============================================================
# BLOCK 6: Profiler hands_observed
# ============================================================
print("\n[6] Profiler: hands_observed")
db3 = OpponentDatabase()
p = db3.get("TestPlayer")
check("Initial hands_observed = 0", p.hands_observed == 0)
check("Initial probe_complete = False", p.probe_complete is False)
for _ in range(20):
    db3.record_preflop_action("TestPlayer", "call", facing_raise=False)
check("After 20 hands: hands_observed = 20",
      p.hands_observed == 20, "got " + str(p.hands_observed))
check("After 20 hands: probe_complete = True",
      p.probe_complete is True)

# ============================================================
# BLOCK 7: Regression audit (v2 features must still work)
# ============================================================
print("\n[7] Regression Audit")
db4 = OpponentDatabase()
e4 = DecisionEngine(db4)
e4._hands_decided = 100

aa = e4.decide(GameState(
    hole_cards=parse_hand(["As", "Ah"]), board=[],
    pot=150, call_amount=100, our_chips=2000, big_blind=50,
    position="BTN", street="preflop", num_players=2,
    active_opponents=["V"], last_aggressor="V"
))
check("AA raises preflop (regression)",
      aa.action == "raise", aa.reasoning[:50])

akflop = e4.decide(GameState(
    hole_cards=parse_hand(["As", "Ks"]),
    board=parse_hand(["Ah", "7d", "2c"]),
    pot=300, call_amount=0, our_chips=2000, big_blind=50,
    position="BTN", street="flop", num_players=2,
    active_opponents=["V"]
))
check("AKs on A72 bets value (regression)",
      akflop.action in ("bet", "raise"), akflop.reasoning[:50])

trash = e4.decide(GameState(
    hole_cards=parse_hand(["2c", "7h"]), board=[],
    pot=150, call_amount=100, our_chips=2000, big_blind=50,
    position="MP", street="preflop", num_players=6,
    active_opponents=["V"], last_aggressor="V"
))
check("72o folds preflop (regression)",
      trash.action == "fold", trash.reasoning[:50])

# ============================================================
# BLOCK 8: Adaptive Mode Switching (v3.1)
# ============================================================
print("\n[8] Adaptive Mode Switching (v3.1)")
from bot import BetScriptBot

# Test set_aggression runtime switch
from decision_engine import DecisionEngine as DE
db_sw = OpponentDatabase()
e_sw = DE(db_sw, aggression="balanced")
check("set_aggression: balanced -> aggressive",
      e_sw.aggression == "balanced", "start: balanced")
e_sw.set_aggression("aggressive")
check("set_aggression: now aggressive",
      e_sw.aggression == "aggressive", "after set: aggressive")
e_sw.set_aggression("balanced")
check("set_aggression: back to balanced",
      e_sw.aggression == "balanced", "after set: balanced")

# Test adaptive_mode_check on a FISH field (VPIP > 38%)
bot_fish = BetScriptBot(aggression="balanced")
for i in range(25):
    # Simulate a fish: calls everything, never folds
    bot_fish.db.record_preflop_action("Fish1", "call", facing_raise=False)
    bot_fish.db.record_preflop_action("Fish1", "call", facing_raise=True)
    bot_fish.db.record_cbet_response("Fish1", folded=False)   # calls cbets
bot_fish.hand_count = 20
bot_fish.adaptive_mode_check()
check("Fish field -> AGGRESSIVE mode",
      bot_fish.engine.aggression == "aggressive",
      "mode=" + bot_fish.engine.aggression)

# Test adaptive_mode_check on a MANIAC field (AF > 2.5)
# Maniacs raise/bet 3x for every 1 call -> AF = (raises+bets)/calls = 6/2 = 3.0
bot_maniac = BetScriptBot(aggression="balanced")
for i in range(25):
    bot_maniac.db.record_preflop_action("Maniac1", "raise", facing_raise=True)
    bot_maniac.db.record_postflop_action("Maniac1", "raise")   # raise
    bot_maniac.db.record_postflop_action("Maniac1", "bet")     # bet
    bot_maniac.db.record_postflop_action("Maniac1", "bet")     # bet  -> 3 aggressive acts
    bot_maniac.db.record_postflop_action("Maniac1", "call")    # 1 call -> AF = 3/1 = 3.0
    bot_maniac.db.record_cbet_response("Maniac1", folded=False)
bot_maniac.hand_count = 20
bot_maniac.adaptive_mode_check()
check("Maniac field -> BALANCED mode (trap, don't bluff)",
      bot_maniac.engine.aggression == "balanced",
      "mode=" + bot_maniac.engine.aggression)

# Test adaptive_mode_check on a NIT field (VPIP < 18%, AF < 1.5)
bot_nit = BetScriptBot(aggression="balanced")
for i in range(25):
    bot_nit.db.record_preflop_action("Nit1", "fold", facing_raise=True)
    bot_nit.db.record_cbet_response("Nit1", folded=True)   # folds to everything
bot_nit.hand_count = 20
bot_nit.adaptive_mode_check()
check("Nit field -> AGGRESSIVE mode (steal blinds)",
      bot_nit.engine.aggression == "aggressive",
      "mode=" + bot_nit.engine.aggression)

# ============================================================
# SUMMARY
# ============================================================
print()
print("=" * 65)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print("RESULT: " + str(passed) + "/" + str(total) + " PASSED")
if passed == total:
    print("ALL CHECKS PASS. Bot v3.1.0 is competition-ready.")
    sys.exit(0)
else:
    for name, ok, detail in results:
        if not ok:
            print("  FAILED: " + name + " (" + detail + ")")
    sys.exit(1)
