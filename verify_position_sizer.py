"""
verify_position_sizer.py — Article 3 Verification Gate
Tests position_sizer.py integration into numerai_pipeline.py.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "pcdraft"))

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {name}")
        PASS += 1
    else:
        print(f"  [FAIL] {name}: {detail}")
        FAIL += 1

print("=" * 60)
print("Position Sizer -- Verification Suite")
print("=" * 60)

# Block 1: File Existence
print("\n[BLOCK 1] File Existence")
pcdraft = pathlib.Path(r"C:\Users\admin\Downloads\medsumag1\pcdraft")
check("position_sizer.py exists", (pcdraft / "position_sizer.py").exists())
check("numerai_pipeline.py exists", (pcdraft / "numerai_pipeline.py").exists())
check("market_regime_classifier.py exists", (pcdraft / "market_regime_classifier.py").exists())

# Block 2: Module Import
print("\n[BLOCK 2] Module Import")
try:
    from position_sizer import (
        StockPressure, PositionSizer,
        RISK_SAFE, RISK_CAUTION, RISK_DANGER, RISK_CRITICAL
    )
    check("position_sizer imports ok", True)
except Exception as e:
    check("position_sizer imports ok", False, str(e))
    sys.exit(1)

# Block 3: StockPressure Unit Tests
print("\n[BLOCK 3] StockPressure Unit Tests")
import numpy as np

# Safe stock: low deviation, high rank
sp_safe = StockPressure(
    stock_id="safe", feature_deviation=0.3, era_volatility=0.2,
    rank_contribution=0.8, cross_section_size=100,
    alpha_score=0.8, alpha_rank=0.8,
    feature_agreement=0.9, era_dispersion=0.1
)
check("SAFE: drawdown_pressure < 0.15", sp_safe.drawdown_pressure < 0.15,
      f"got {sp_safe.drawdown_pressure:.3f}")
check("SAFE: risk_regime = SAFE", sp_safe.risk_regime == RISK_SAFE,
      f"got {sp_safe.risk_regime}")
check("SAFE: passes_conviction = True", sp_safe.passes_conviction)
check("SAFE: kelly_fraction > 0", sp_safe.kelly_fraction > 0,
      f"got {sp_safe.kelly_fraction:.4f}")
check("SAFE: kelly_fraction <= 0.25", sp_safe.kelly_fraction <= 0.25)

# Danger stock: high deviation, low rank
sp_danger = StockPressure(
    stock_id="danger", feature_deviation=1.8, era_volatility=0.5,
    rank_contribution=0.3, cross_section_size=100,
    alpha_score=0.3, alpha_rank=0.3,
    feature_agreement=0.3, era_dispersion=0.6
)
check("DANGER: drawdown_pressure > 0.3", sp_danger.drawdown_pressure > 0.3,
      f"got {sp_danger.drawdown_pressure:.3f}")
check("DANGER: passes_conviction = False", not sp_danger.passes_conviction)
check("DANGER: kelly_fraction = 0", sp_danger.kelly_fraction == 0.0)

# Risk premium checks
check("risk_premium >= 0.04 floor (safe)", sp_safe.risk_premium >= 0.04)
check("risk_premium >= 0.04 floor (danger)", sp_danger.risk_premium >= 0.04)
check("risk_premium danger > risk_premium safe",
      sp_danger.risk_premium > sp_safe.risk_premium)

check("sizing_features() returns 13 keys", len(sp_safe.sizing_features()) == 13,
      f"got {len(sp_safe.sizing_features())}")

# Block 4: PositionSizer Integration
print("\n[BLOCK 4] PositionSizer Integration")
import pandas as pd

np.random.seed(42)
n = 150
feats = [f"feature_{i:03d}" for i in range(10)]
df1 = pd.DataFrame(np.random.normal(0.5, 0.3, (n, 10)), columns=feats)
df1["era"] = "era_001"
df2 = pd.DataFrame(np.random.normal(0.7, 0.05, (n, 10)), columns=feats)
df2["era"] = "era_002"
df = pd.concat([df1, df2], ignore_index=True)

sizer = PositionSizer(feature_cols=feats)
result = sizer.get_sizing_feature_matrix(df, era_col="era")

sizing_cols = [c for c in result.columns if c.startswith("sizing_")]
check("PositionSizer adds >= 13 sizing_ columns", len(sizing_cols) >= 13,
      f"got {len(sizing_cols)}")
check("sizing_drawdown_pressure has non-zero variance",
      result["sizing_drawdown_pressure"].std() > 0)
check("sizing_kelly_fraction has non-zero variance",
      result["sizing_kelly_fraction"].std() > 0)
check("sizing_kelly_fraction max <= 0.25",
      result["sizing_kelly_fraction"].max() <= 0.25)
check("No NaN in sizing columns",
      result[sizing_cols].isna().sum().sum() == 0)

# Block 5: Pipeline Integration Check
print("\n[BLOCK 5] Pipeline Integration Check")
pipeline_text = (pcdraft / "numerai_pipeline.py").read_text(encoding="utf-8")
check("Pipeline imports PositionSizer",
      "from position_sizer import PositionSizer" in pipeline_text)
check("Pipeline uses get_sizing_feature_matrix",
      "get_sizing_feature_matrix" in pipeline_text)
check("Pipeline still imports MarketProfiler",
      "from market_regime_classifier import MarketProfiler" in pipeline_text)
check("Fallback path still present", "fallback" in pipeline_text.lower())

# Block 6: Regression
print("\n[BLOCK 6] Regression Checks")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("numerai_pipeline", pcdraft / "numerai_pipeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    check("numerai_pipeline.py loads without error", True)
    for fn in ["download_data", "train_model", "submit_predictions",
               "engineer_features", "_resolve_model_uuid"]:
        check(f"{fn} function present", hasattr(mod, fn))
except Exception as e:
    check("numerai_pipeline.py loads without error", False, str(e))

# Final Gate
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"Results: {PASS}/{total} PASS | {FAIL} FAIL")
if FAIL == 0:
    print("STATUS: ALL CHECKS PASSED")
    sys.exit(0)
else:
    print("STATUS: SOME CHECKS FAILED")
    sys.exit(1)
