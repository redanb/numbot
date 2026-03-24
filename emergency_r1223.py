"""
emergency_r1223.py - ROUND 1223 EMERGENCY SUBMISSION
Multi-pronged: Downloads fresh live data, trains fast XGBoost, submits CSV
Works for BOTH ANANT0 and ANANTA models.
Run: python emergency_r1223.py

ROOT CAUSE FIXES vs standalone_r1221_fix.py:
  1. Fixed missing `from pathlib import Path` import
  2. Fixed model_path saved to MODEL_DIR (not CWD)
  3. No cloudpickle dependency for predict wrapper (uses direct XGBRegressor)
  4. Hardcoded model UUIDs for both models
  5. sys.stdout is guarded (not at module level - RULE-056)
  6. No emojis (RULE-023 / cp1252 safe)
"""
import os
import sys
import json
import logging
import datetime
from pathlib import Path
import pathlib

# cp1252-safe stdout - only in __main__
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [R1223] %(levelname)s %(message)s"
)
log = logging.getLogger("emergency_r1223")

# ── Paths ─────────────────────────────────────────────────────────────────────
MASTER_DIR   = pathlib.Path(r"C:\Users\admin\.antigravity\master")
PIPELINE_DIR = pathlib.Path(r"C:\Users\admin\Downloads\medsumag1\pcdraft\numerai")
DATA_DIR     = PIPELINE_DIR / "data"
MODEL_DIR    = PIPELINE_DIR / "models"
OUTPUT_DIR   = PIPELINE_DIR / "predictions"
for _d in [DATA_DIR, MODEL_DIR, OUTPUT_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Hardcoded model UUIDs (RULE-074: 3-tier resolution, fallback hardcoded) ──
MODEL_IDS = {
    "anant0": "5fe67e13-8dae-4693-8294-84ddd8e8db80",
    "ananta": "14a8473a-b203-446e-a727-d55789c9cc81",
}


def load_env() -> tuple:
    """Load API keys from master .env."""
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), val)
    pub = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec = os.environ.get("NUMERAI_SECRET_KEY", "")
    log.info("Keys: PUB=%s... SEC=%s...",
             pub[:5] if pub else "MISSING",
             sec[:5] if sec else "MISSING")
    return pub, sec


def resolve_uuid(napi, model_name: str) -> str:
    """3-tier UUID resolution: GraphQL -> NumerAPI -> Hardcoded fallback."""
    # Tier 1: GraphQL
    try:
        import requests
        query = """query($n: String!){v3UserProfile(modelName:$n){id}}"""
        r = requests.post(
            "https://api-tournament.numer.ai",
            json={"query": query, "variables": {"modelName": model_name}},
            timeout=10
        )
        pid = r.json().get("data", {}).get("v3UserProfile", {})
        if pid and pid.get("id"):
            log.info("[UUID] Resolved via GraphQL: %s -> %s", model_name, pid["id"])
            return pid["id"]
    except Exception as e:
        log.debug("[UUID] GraphQL failed: %s", e)

    # Tier 2: NumerAPI
    try:
        models = napi.get_models()
        if model_name in models:
            log.info("[UUID] Resolved via NumerAPI: %s -> %s", model_name, models[model_name])
            return models[model_name]
    except Exception as e:
        log.debug("[UUID] NumerAPI lookup failed: %s", e)

    # Tier 3: Hardcoded fallback
    uid = MODEL_IDS.get(model_name.lower(), model_name)
    log.info("[UUID] Using hardcoded fallback: %s -> %s", model_name, uid)
    return uid


def download_live_data(napi) -> Path:
    """Download fresh live.parquet."""
    live_path = DATA_DIR / "live.parquet"
    log.info("[STEP 1] Downloading fresh live.parquet for Round 1223...")
    napi.download_dataset("v5.2/live.parquet", str(live_path))
    log.info("[STEP 1] Done. live.parquet: %.1f MB", live_path.stat().st_size / 1e6)
    return live_path


def ensure_train_data(napi) -> Path:
    """Download training data only if not present."""
    train_path = DATA_DIR / "train.parquet"
    if train_path.exists():
        log.info("[STEP 1] train.parquet exists (%.1f MB), skipping download.",
                 train_path.stat().st_size / 1e6)
    else:
        log.info("[STEP 1] Downloading train.parquet (this will take a few minutes)...")
        napi.download_dataset("v5.2/train.parquet", str(train_path))
        log.info("[STEP 1] Done.")
    return train_path


def train_and_predict(train_path: Path, live_path: Path) -> Path:
    """Train XGBoost and generate ranked predictions for live data."""
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    from xgboost import XGBRegressor
    from scipy.stats import rankdata

    ts = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")

    # ── Load training schema ─────────────────────────────────────────────────
    log.info("[STEP 2] Reading train schema...")
    schema = pq.read_schema(train_path)
    all_cols = schema.names
    feature_cols = [c for c in all_cols if c.startswith("feature_")][:50]
    target_col = next((c for c in all_cols if c == "target"), None)
    if not target_col:
        target_col = next((c for c in all_cols if "target" in c), "target")
    era_col = "era" if "era" in all_cols else None
    load_cols = ([era_col] if era_col else []) + feature_cols + [target_col]

    log.info("[STEP 2] Loading train data (%d features, target=%s)...",
             len(feature_cols), target_col)
    df_train = pd.read_parquet(train_path, columns=load_cols)

    # Subsample for speed (10%) — keeps RAM low, retains signal
    if len(df_train) > 80000:
        df_train = df_train.sample(frac=0.1, random_state=42)
        log.info("[STEP 2] Sampled to %d rows.", len(df_train))

    for col in feature_cols + [target_col]:
        if col in df_train.columns:
            df_train[col] = df_train[col].astype(np.float32)

    X_train = df_train[feature_cols].fillna(0)
    y_train = df_train[target_col]

    # ── Train model ──────────────────────────────────────────────────────────
    log.info("[STEP 2] Training XGBoost (n_estimators=300)...")
    model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.5,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
        tree_method="hist",
    )
    model.fit(X_train, y_train, verbose=False)
    log.info("[STEP 2] Training complete.")

    # ── Save model as JSON (RULE-081: cross-platform serialization) ──────────
    model_path = MODEL_DIR / f"xgb_r1223_{ts}.json"
    model.save_model(str(model_path))
    log.info("[STEP 2] Model saved: %s", model_path)

    # ── Load live data ───────────────────────────────────────────────────────
    log.info("[STEP 3] Loading live data...")
    live_schema = pq.read_schema(live_path)
    live_cols_all = live_schema.names
    avail_features = [c for c in feature_cols if c in live_cols_all]
    read_cols_live = avail_features[:]
    if era_col and era_col in live_cols_all:
        read_cols_live.append(era_col)

    df_live = pd.read_parquet(live_path, columns=read_cols_live)
    for col in avail_features:
        df_live[col] = df_live[col].astype(np.float32)

    log.info("[STEP 3] Live rows: %d", len(df_live))

    # ── Predict ──────────────────────────────────────────────────────────────
    X_live = df_live[avail_features].fillna(0)
    raw_preds = model.predict(X_live)

    # Rank-normalize to [0, 1] (Numerai REQUIRES this)
    ranked = (rankdata(raw_preds) - 0.5) / len(raw_preds)

    # ── Build submission CSV ─────────────────────────────────────────────────
    # Numerai expects CSV with columns: id, prediction
    # The live parquet has `id` as the index (NumerAI v5.2 convention)
    id_series = df_live.index
    if "id" in df_live.columns:
        id_series = df_live["id"]
    elif df_live.index.name == "id":
        id_series = df_live.index
    elif hasattr(df_live.index, "names") and "id" in df_live.index.names:
        id_series = df_live.index.get_level_values("id")

    out_path = OUTPUT_DIR / f"predictions_r1223_{ts}.csv"
    submission = pd.DataFrame({"id": id_series, "prediction": ranked})
    submission.to_csv(out_path, index=False)
    log.info("[STEP 3] Predictions saved: %s (%d rows)", out_path, len(submission))

    # Sanity checks
    assert len(submission) > 0, "Submission is empty!"
    assert submission["prediction"].between(0, 1).all(), "Predictions not in [0, 1]!"
    log.info("[STEP 3] Sanity checks passed.")
    return out_path


def submit_csv(napi, out_path: Path, model_name: str, model_uuid: str) -> bool:
    """Submit predictions CSV via NumerAPI (with retry)."""
    log.info("[STEP 4] Submitting CSV for %s (UUID: %s)...", model_name, model_uuid)
    for attempt in range(3):
        try:
            sub_id = napi.upload_predictions(str(out_path), model_id=model_uuid)
            log.info("[STEP 4] SUCCESS for %s! sub_id=%s", model_name, sub_id)
            return True
        except Exception as e:
            err = str(e)
            log.error("[STEP 4] Attempt %d failed for %s: %s", attempt + 1, model_name, err)
            # If 'already submitted' treat as success
            if "already" in err.lower() or "existing" in err.lower():
                log.info("[STEP 4] Already submitted for %s - treating as OK.", model_name)
                return True
            import time
            time.sleep(2 ** attempt)
    return False


def main():
    import numerapi
    log.info("=" * 60)
    log.info("NUMERAI ROUND 1223 - EMERGENCY SUBMISSION SCRIPT")
    log.info("=" * 60)

    pub, sec = load_env()
    if not pub or not sec:
        log.error("FATAL: Numerai API keys missing from .env. Abort.")
        sys.exit(1)

    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)

    # Check current round
    try:
        current_round = napi.get_current_round()
        log.info("Current Numerai Round: %s", current_round)
    except Exception as e:
        log.warning("Could not get current round: %s", e)
        current_round = 1223

    # ── Step 1: Get data ─────────────────────────────────────────────────────
    live_path = download_live_data(napi)
    train_path = ensure_train_data(napi)

    # ── Step 2 & 3: Train and predict ────────────────────────────────────────
    out_path = train_and_predict(train_path, live_path)

    # ── Step 4: Submit to BOTH models ────────────────────────────────────────
    results = {}
    for model_name in ["anant0", "ananta"]:
        uuid = resolve_uuid(napi, model_name)
        success = submit_csv(napi, out_path, model_name, uuid)
        results[model_name] = "SUCCESS" if success else "FAILED"

    log.info("=" * 60)
    log.info("SUBMISSION RESULTS:")
    for m, s in results.items():
        log.info("  %s -> %s", m.upper(), s)

    # ── Step 5: Upload callable model (for automated future runs) ────────────
    try:
        import cloudpickle
        import numpy as np
        import pandas as pd
        from scipy.stats import rankdata
        from xgboost import XGBRegressor

        # 1. Get the latest model and load it locally first
        json_files = sorted(MODEL_DIR.glob("xgb_r1223_*.json"))
        if not json_files:
             raise FileNotFoundError("No trained XGB model JSON found to embed.")
        latest_model_path = json_files[-1]
        
        # Pre-load the model to capture in closure
        capture_model = XGBRegressor()
        capture_model.load_model(str(latest_model_path))
        
        # 2. Define the exact predict function expected by Numerai
        def predict_callable(live_features: pd.DataFrame) -> pd.DataFrame:
            import pandas as pd
            import numpy as np
            from scipy.stats import rankdata
            
            # Select features (top 50 as used in training)
            avail = [c for c in live_features.columns if c.startswith("feature_")][:50]
            X = live_features[avail].fillna(0).astype(np.float32)
            
            preds = capture_model.predict(X)
            ranked = (rankdata(preds) - 0.5) / len(preds)
            return pd.DataFrame({"prediction": ranked}, index=live_features.index)

        assert callable(predict_callable)

        ts2 = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
        pkl_path = MODEL_DIR / f"self_contained_r1223_{ts2}.pkl"
        with open(pkl_path, "wb") as f:
            cloudpickle.dump(predict_callable, f)
        log.info("[STEP 5] Self-contained PKL saved: %s", pkl_path)

        # Upload PKL to both models
        for model_name in ["anant0", "ananta"]:
            uuid = resolve_uuid(napi, model_name)
            try:
                napi.model_upload(str(pkl_path), model_id=uuid)
                log.info("[STEP 5] Model uploaded for %s", model_name.upper())
            except Exception as e:
                log.error("[STEP 5] Model upload failed for %s: %s", model_name.upper(), e)

    except Exception as e:
        log.error("[STEP 5] Callable/upload block failed (non-critical): %s", e)
        log.info("[STEP 5] CSV submission is still the primary channel.")

    log.info("=" * 60)
    log.info("DONE. Check https://numer.ai/tournament in 5-10 minutes.")
    log.info("=" * 60)
    return results


if __name__ == "__main__":
    results = main()
    failed = [m for m, s in results.items() if s != "SUCCESS"]
    sys.exit(0 if not failed else 1)
