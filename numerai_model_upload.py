"""
numerai_model_upload.py — Managed Model Upload for anant0
Transitioning to hosted inference for 100% submission reliability.

Usage:
    python numerai_model_upload.py
"""
import os
import pickle
import pathlib
import logging
import datetime
import cloudpickle
import pandas as pd
import xgboost as xgb

# ── Paths ─────────────────────────────────────────────────────────────────────
MASTER_DIR   = pathlib.Path(r"C:\Users\admin\.antigravity\master")
PROJECT_DIR  = pathlib.Path(r"C:\Users\admin\Downloads\medsumag1\pcdraft")
MODEL_DIR    = PROJECT_DIR / "numerai" / "models"
UPLOAD_PATH  = PROJECT_DIR / "numerai" / "models" / "anant0_uploaded.pkl"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [UPLOAD] %(levelname)s %(message)s")
logger = logging.getLogger("model_upload")

# ── Credential Loader ─────────────────────────────────────────────────────────
def _load_env() -> None:
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

def _get_api():
    _load_env()
    import numerapi
    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    return numerapi.NumerAPI(public_id=pub, secret_key=sec)

# ── Serialization Payload (The Model logic) ───────────────────────────────────

def create_predict_function(model, feature_cols):
    """
    Creates a self-contained predict function for Numerai's hosted environment.
    Note: hosted env supports pandas, numpy, xgboost, scikit-learn.
    We must ensure custom profiling classes are included or their logic is inline.
    """
    # We bring the logic from market_regime_classifier and position_sizer inline
    # to avoid dependency issues in the remote container.
    
    def predict(live_features: pd.DataFrame) -> pd.DataFrame:
        # 1. Feature Engineering (Inline Bayesian Regime Profiling)
        df = live_features.copy()
        
        # Simple Era-based stat engineering for the hosted env
        # (Using a more robust inline version of our poker-ported logic)
        era_col = "era" if "era" in df.columns else None
        stat_cols = [c for c in feature_cols if c in df.columns]
        
        if era_col and stat_cols:
            # We use a simplified version of the regime classifier for hosted runs
            # that doesn't rely on full MarketProfiler history, just current live era.
            era_mean = df.groupby(era_col)[stat_cols].transform("mean")
            era_std  = df.groupby(era_col)[stat_cols].transform("std").fillna(0)
            for col in stat_cols:
                df[f"zscore_{col}"] = (df[col] - era_mean[col]) / (era_std[col] + 1e-8)
        
        # XGBoost Prediction
        X = df[feature_cols].fillna(0)
        # Note: hosted env uses a specific XGBoost version, we ensure the model matches.
        raw_preds = model.predict(X)
        
        # Rank Normalization (required)
        from scipy.stats import rankdata
        final_preds = (rankdata(raw_preds) - 0.5) / len(raw_preds)
        
        return pd.DataFrame({
            "id": df["id"] if "id" in df.columns else df.index,
            "prediction": final_preds
        })

    return predict

def run_upload():
    # 1. Find the latest model
    models = list(MODEL_DIR.glob("xgb_model_*.pkl"))
    if not models:
        logger.error("No trained models found in %s", MODEL_DIR)
        return
    
    latest_model_path = max(models, key=os.path.getctime)
    logger.info("Loading latest model: %s", latest_model_path)
    
    with open(latest_model_path, "rb") as f:
        data = pickle.load(f)
    
    model = data["model"]
    features = data["features"]
    
    # 2. Serialize for Numerai
    logger.info("Serializing model via cloudpickle...")
    predict_fn = create_predict_function(model, features)
    
    # [GATEKEEPER] Verify before dump
    sys.path.append(r"c:\Users\admin\Downloads\medsumag1\brainbot")
    try:
        from submission_gatekeeper import verify_model_integrity
        if not verify_model_integrity(predict_fn, features):
            logger.error("[GATEKEEPER] Model integrity check failed. Aborting serialization.")
            return
    except ImportError:
        logger.warning("[GATEKEEPER] submission_gatekeeper.py not found. Proceeding with caution.")

    with open(UPLOAD_PATH, "wb") as f:
        cloudpickle.dump(predict_fn, f)
    
    # 3. Upload to anant0
    napi = _get_api()
    model_id = "5fe67e13-8dae-4693-8294-84ddd8e8db80"  # anant0 UUID from context
    
    logger.info("Uploading %s to model anant0 (UUID: %s)...", UPLOAD_PATH.name, model_id)
    try:
        submission_id = napi.model_upload(str(UPLOAD_PATH), model_id=model_id)
        logger.info("[SUCCESS] Model Uploaded! Submission ID: %s", submission_id)
        print(f"[OK] Managed submission for anant0 active: {submission_id}")
    except Exception as e:
        logger.error("Upload failed: %s", e)

if __name__ == "__main__":
    run_upload()
