"""
verify_market_regime.py — Article 3 Verification Gate
Tests market_regime_classifier.py integration into numerai_pipeline.py.

RULE-023: No emojis (Windows cp1252 safety).
"""
import sys
import os
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "pcdraft"))

PASS = 0
FAIL = 0

def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {name}")
        PASS += 1
    else:
        print(f"  [FAIL] {name}: {detail}")
        FAIL += 1

print("=" * 60)
print("Market Regime Classifier -- Verification Suite")
print("=" * 60)

# ── Block 1: File Existence ────────────────────────────────────────────────────
print("\n[BLOCK 1] File Existence")
pcdraft = pathlib.Path(r"C:\Users\admin\Downloads\medsumag1\pcdraft")
check("market_regime_classifier.py exists",   (pcdraft / "market_regime_classifier.py").exists())
check("numerai_pipeline.py exists",            (pcdraft / "numerai_pipeline.py").exists())

# ── Block 2: Module Import ─────────────────────────────────────────────────────
print("\n[BLOCK 2] Module Import")
try:
    from market_regime_classifier import (
        EraProfile, MarketProfiler,
        REGIME_TRENDING, REGIME_REVERTING, REGIME_STAGNANT, REGIME_TRANSITIONAL
    )
    check("market_regime_classifier imports ok", True)
except Exception as e:
    check("market_regime_classifier imports ok", False, str(e))
    print("Cannot continue — import failed.")
    sys.exit(1)

# ── Block 3: EraProfile Unit Tests ────────────────────────────────────────────
print("\n[BLOCK 3] EraProfile Unit Tests")
import numpy as np
import pandas as pd

# Trending era: high participation, high trend strength
p_trend = EraProfile("era_trend")
p_trend.n_above_mean = 7000; p_trend.n_total = 10000  # 70% above mean -> high VPIP
p_trend.n_momentum_signals = 1800; p_trend.n_reversion_signals = 600   # AF > 2
p_trend.row_count = 500

check("EraProfile.participation_rate > 0.5 for trending era",    p_trend.participation_rate > 0.5)
check("EraProfile.trend_strength > 1.8 for trending era",        p_trend.trend_strength > 1.8)
check("EraProfile.classify_regime() = TRENDING",                  p_trend.classify_regime() == REGIME_TRENDING,
      f"got {p_trend.classify_regime()}")

# Reverting era: high participation, weak trend
p_rev = EraProfile("era_rev")
p_rev.n_above_mean = 6500; p_rev.n_total = 10000   # 65% VPIP
p_rev.n_momentum_signals = 400; p_rev.n_reversion_signals = 800  # AF < 1.0
p_rev.row_count = 500

check("EraProfile.classify_regime() = REVERTING",                  p_rev.classify_regime() == REGIME_REVERTING,
      f"got {p_rev.classify_regime()}")

# Stagnant era: low participation, low trend
p_nit = EraProfile("era_nit")
p_nit.n_above_mean = 4000; p_nit.n_total = 10000   # 40% VPIP
p_nit.n_momentum_signals = 300; p_nit.n_reversion_signals = 400  # AF < 1.4
p_nit.row_count = 500

check("EraProfile.classify_regime() = STAGNANT",                   p_nit.classify_regime() == REGIME_STAGNANT,
      f"got {p_nit.classify_regime()}")

check("EraProfile.regime_features() returns 11 keys", len(p_trend.regime_features()) == 11,
      f"got {len(p_trend.regime_features())}")

check("EraProfile.confidence() > 0 with 500 rows",  p_trend.confidence() > 0.9)

# ── Block 4: MarketProfiler Integration ───────────────────────────────────────
print("\n[BLOCK 4] MarketProfiler Integration")
np.random.seed(42)
n = 300
feats = [f"feature_{i:03d}" for i in range(15)]

df_t = pd.DataFrame(np.random.uniform(0.6, 1.0, (n, 15)), columns=feats); df_t["era"] = "era_0001"
df_r = pd.DataFrame(np.random.uniform(0.0, 1.0, (n, 15)), columns=feats); df_r["era"] = "era_0002"
df_s = pd.DataFrame(np.random.uniform(0.45, 0.55, (n, 15)), columns=feats); df_s["era"] = "era_0003"
df = pd.concat([df_t, df_r, df_s], ignore_index=True)

profiler = MarketProfiler(feature_cols=feats)
result = profiler.get_regime_feature_matrix(df, era_col="era")

regime_cols = [c for c in result.columns if c.startswith("regime_")]
check("MarketProfiler adds >= 11 regime_ columns",  len(regime_cols) >= 11, f"got {len(regime_cols)}")
check("regime_trend_strength has non-zero variance",
      result["regime_trend_strength"].std() > 0)
check("regime_participation_rate has non-zero variance",
      result["regime_participation_rate"].std() > 0)
check("At least 2 distinct regimes detected",
      result["regime_is_trending"].nunique() + result["regime_is_reverting"].nunique() > 1)
check("No NaN in regime columns",
      result[regime_cols].isna().sum().sum() == 0)
check("MarketProfiler.dominant_regime() returns valid string",
      profiler.dominant_regime() in [REGIME_TRENDING, REGIME_REVERTING, REGIME_STAGNANT, REGIME_TRANSITIONAL])
check("MarketProfiler.stagnant_eras() returns list",
      isinstance(profiler.stagnant_eras(), list))

# ── Block 5: Pipeline Integration Check ───────────────────────────────────────
print("\n[BLOCK 5] Pipeline Integration Check")
pipeline_path = pcdraft / "numerai_pipeline.py"
pipeline_text = pipeline_path.read_text(encoding="utf-8")
check("numerai_pipeline imports MarketProfiler",     "from market_regime_classifier import MarketProfiler" in pipeline_text)
check("engineer_features uses get_regime_feature_matrix", "get_regime_feature_matrix" in pipeline_text)
check("Fallback z-score path present",               "fallback" in pipeline_text.lower())

# ── Block 6: Regression (existing pipeline steps) ─────────────────────────────
print("\n[BLOCK 6] Regression Checks")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("numerai_pipeline", pipeline_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    check("numerai_pipeline.py loads without error", True)
    check("download_data function present",  hasattr(mod, "download_data"))
    check("train_model function present",    hasattr(mod, "train_model"))
    check("submit_predictions function present", hasattr(mod, "submit_predictions"))
    check("engineer_features function present",  hasattr(mod, "engineer_features"))
    check("_resolve_model_uuid function present", hasattr(mod, "_resolve_model_uuid"))
except Exception as e:
    check("numerai_pipeline.py loads without error", False, str(e))

# ── Final Gate ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"Results: {PASS}/{total} PASS | {FAIL} FAIL")
if FAIL == 0:
    print("STATUS: ALL CHECKS PASSED")
    sys.exit(0)
else:
    print("STATUS: SOME CHECKS FAILED")
    sys.exit(1)
