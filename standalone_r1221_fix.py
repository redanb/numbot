"""
standalone_r1221_fix.py - Completely standalone emergency fix for Round 1221.
No external imports from other modules. Self-contained.

Run: python standalone_r1221_fix.py  (from comp bet dir via shell, or directly)
"""
import os, sys, json, logging, datetime, pathlib, pickle
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [R1221] %(message)s")
log = logging.getLogger()

MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")
PIPELINE_DIR = pathlib.Path(r"C:\Users\admin\Downloads\medsumag1\pcdraft\numerai")
DATA_DIR = PIPELINE_DIR / "data"
MODEL_DIR = PIPELINE_DIR / "models"
OUTPUT_DIR = PIPELINE_DIR / "predictions"
for d in [DATA_DIR, MODEL_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def load_env():
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
    log.info("Numerai API Keys loaded: PUB=%s... SEC=%s...", pub[:5] if pub else "MISSING", sec[:5] if sec else "MISSING")
    return pub, sec

def main():
    import numerapi
    import pandas as pd
    import numpy as np
    import pyarrow.parquet as pq
    from xgboost import XGBRegressor
    from sklearn.model_selection import KFold
    from scipy.stats import spearmanr, rankdata
    import cloudpickle

    log.info("=" * 55)
    log.info("ROUND 1221 EMERGENCY FIX")
    log.info("=" * 55)

    pub, sec = load_env()
    if not pub or not sec:
        log.error("FATAL: Numerai API keys not found in .env")
        return

    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
    current_round = napi.get_current_round()
    log.info("Current Numerai Round: %s", current_round)

    # ── Step 1: Download live data ──────────────────────────────────────────
    train_path = DATA_DIR / "train.parquet"
    live_path  = DATA_DIR / "live.parquet"

    if not train_path.exists():
        log.info("[STEP 1] Downloading training data...")
        napi.download_dataset("v5.2/train.parquet", str(train_path))
    else:
        log.info("[STEP 1] Training data already exists, skipping download.")

    log.info("[STEP 1] Downloading fresh live data...")
    napi.download_dataset("v5.2/live.parquet", str(live_path))
    log.info("[STEP 1] Done.")

    # ── Step 2: Train model ─────────────────────────────────────────────────
    log.info("[STEP 2] Loading training features...")
    schema = pq.read_schema(train_path)
    all_cols = schema.names
    feature_cols = [c for c in all_cols if c.startswith("feature_")][:50]
    target_col = next((c for c in all_cols if "target" == c), None)
    if not target_col:
        target_col = next(c for c in all_cols if "target" in c)
    era_col = "era"
    load_cols = [era_col] + feature_cols + [target_col]

    log.info("[STEP 2] Loading data - %d features + target", len(feature_cols))
    df = pd.read_parquet(train_path, columns=load_cols)
    if len(df) > 100000:
        df = df.sample(frac=0.1, random_state=42)
        log.info("[STEP 2] Sampled to %d rows for memory efficiency", len(df))
    for col in feature_cols + [target_col]:
        df[col] = df[col].astype(np.float32)

    # Train XGBoost
    log.info("[STEP 2] Training XGBoost model...")
    X = df[feature_cols].fillna(0)
    y = df[target_col]
    final_model = XGBRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=5,
        subsample=0.8, colsample_bytree=0.5, random_state=42,
        n_jobs=-1, verbosity=0
    )
    final_model.fit(X, y, verbose=False)
    
    # Quick CV score
    cv_preds = final_model.predict(X)
    score, _ = spearmanr(cv_preds, y)
    log.info("[STEP 2] Training Spearman (train set): %.4f", score)

    # ── CRITICAL: Wrap in CALLABLE ──────────────────────────────────────────
    _feature_cols = feature_cols  # capture for closure
    
    # Save booster to JSON to avoid C-extension pickling issues across OS
    model_path = Path("model.json")
    final_model.save_model(str(model_path))

    def predict(live_features: pd.DataFrame, live_benchmark_models: pd.DataFrame) -> pd.DataFrame:
        """Standard Numerai Compute signature: takes features & benchmarks, returns DataFrame."""
        import pandas as pd
        import numpy as np
        import xgboost as xgb
        from scipy.stats import rankdata

        # Load model from JSON file saved on disk
        m = xgb.XGBRegressor()
        m.load_model(str(model_path))

        avail = [c for c in _feature_cols if c in live_features.columns]
        X_live = live_features[avail].fillna(0).astype(np.float32)
        
        preds = m.predict(X_live)
        
        # Rank-normalize
        ranked = (rankdata(preds) - 0.5) / len(preds)
        
        # Return standard DataFrame
        return pd.DataFrame({"prediction": ranked}, index=live_features.index)

    # Verify it's callable
    assert callable(predict), "predict must be callable!"
    log.info("[STEP 2] Standardized callable created. callable=%s", callable(predict))

    # Save callable pickle
    ts = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    pkl_path = MODEL_DIR / f"callable_r1221_{ts}.pkl"
    with open(pkl_path, "wb") as f:
        cloudpickle.dump(predict, f)
    log.info("[STEP 2] Saved callable PKL to %s", pkl_path)

    # Verify the saved pickle is callable
    with open(pkl_path, "rb") as f:
        loaded = cloudpickle.load(f)
    assert callable(loaded), "Loaded PKL must be callable!"
    log.info("[STEP 2] Verified: loaded PKL is callable: %s", callable(loaded))

    # ── Step 3: Generate predictions CSV ───────────────────────────────────
    log.info("[STEP 3] Loading live data for predictions...")
    live_schema = pq.read_schema(live_path)
    live_cols = live_schema.names
    
    # Identify features available in live data
    avail_features = [c for c in feature_cols if c in live_cols]
    load_live = avail_features.copy()
    if "id" in live_cols: load_live.append("id")
    if era_col in live_cols: load_live.append(era_col)
    
    # Read without 'id' if 'id' is in columns but might be index
    read_cols = [c for c in load_live if c != "id"]
    df_live = pd.read_parquet(live_path, columns=read_cols)
    
    # Identify ID series for submission
    id_series = df_live.index
    if "id" in df_live.columns:
        id_series = df_live["id"]
    elif df_live.index.name == "id" or "id" in df_live.index.names:
        id_series = df_live.index.get_level_values("id") if isinstance(df_live.index, pd.MultiIndex) else df_live.index
    
    for col in avail_features:
        df_live[col] = df_live[col].astype(np.float32)

    log.info("[STEP 3] Generating predictions on %d live rows...", len(df_live))
    # Pass empty dummy benchmarks for local verification
    preds_df = predict(df_live, pd.DataFrame())
    preds_series = preds_df["prediction"]
    
    out_path = OUTPUT_DIR / f"predictions_r1221_{ts}.csv"
    submission = pd.DataFrame({"id": id_series, "prediction": preds_series.values})
    submission.to_csv(out_path, index=False)
    log.info("[STEP 3] Predictions saved to %s (%d rows)", out_path, len(submission))

    # ── Step 4: Submit CSV predictions ─────────────────────────────────────
    ANANT0_UUID = "5fe67e13-8dae-4693-8294-84ddd8e8db80"
    log.info("[STEP 4] Submitting CSV for ANANT0 (UUID: %s)...", ANANT0_UUID)
    try:
        sub_id = napi.upload_predictions(str(out_path), model_id=ANANT0_UUID)
        log.info("[STEP 4] SUCCESS! Submission ID: %s", sub_id)
    except Exception as e:
        log.error("[STEP 4] CSV submit failed: %s", e)

    # ── Step 5: Upload new callable PKL to Numerai Compute ─────────────────
    log.info("[STEP 5] Uploading callable PKL to Numerai Compute (ANANT0)...")
    try:
        napi.model_upload(str(pkl_path), model_id=ANANT0_UUID)
        log.info("[STEP 5] Model PKL uploaded successfully!")
    except Exception as e:
        log.error("[STEP 5] Model upload failed: %s", e)

    log.info("=" * 55)
    log.info("DONE. Check https://numer.ai/tournament#submissions in 5 min.")
    log.info("=" * 55)

if __name__ == "__main__":
    main()
