import os
import sys
import logging
import datetime
import cloudpickle
import pandas as pd
import xgboost as xgb
from numerapi import NumerAPI

# --- CONFIGURATION ---
MODELS = {
    "anant0": "5fe67e13-8dae-4693-8294-84ddd8e8db80",
    "ananta": "14a8473a-b203-446e-a727-d55789c9cc81"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NumeraiSentinel")

def create_emergency_model(model_name):
    """Creates a basic but valid callable model to repair 'Failed' states."""
    logger.info(f"Generating emergency repair model for {model_name}...")
    model = xgb.XGBRegressor(n_estimators=100, max_depth=3)
    # Mock data for structural fit
    import numpy as np
    model.fit(np.random.rand(10, 50), np.random.rand(10))
    
    def predict(live_features: pd.DataFrame) -> pd.DataFrame:
        import pandas as pd
        import numpy as np
        from scipy.stats import rankdata
        feature_cols = [c for c in live_features.columns if c.startswith("feature_")][:50]
        if not feature_cols: feature_cols = live_features.columns[:50]
        X = live_features[feature_cols].fillna(0).astype(np.float32)
        if X.shape[1] < 50:
            X_vals = np.pad(X.values, ((0,0), (0, 50 - X.shape[1])))
        else:
            X_vals = X.values
        preds = model.predict(X_vals)
        ranked = (rankdata(preds) - 0.5) / len(preds)
        return pd.DataFrame({'prediction': ranked}, index=live_features.index)
        
    path = f"{model_name}_repair.pkl"
    with open(path, "wb") as f:
        cloudpickle.dump(predict, f)
    return path

def check_and_repair():
    public_id = os.getenv("NUMERAI_PUBLIC_ID")
    secret_key = os.getenv("NUMERAI_SECRET_KEY")
    
    if not public_id or not secret_key:
        logger.error("Missing credentials for Sentinel.")
        return

    napi = NumerAPI(public_id, secret_key)
    print("Fetching current round...")
    current_round = napi.get_current_round()
    logger.info(f"Sentinel checking Round {current_round}...")

    for model_name, model_id in MODELS.items():
        print(f"Checking model: {model_name}...")
        logger.info(f"Verifying {model_name} ({model_id})...")
        try:
            print(f"Fetching sub-ids for {model_name}...")
            subs = napi.submission_ids(model_id)
            print(f"Found {len(subs)} submissions.")
            latest_sub = None
            if subs:
                 # Find first sub matching current round
                 round_subs = [s for s in subs if s.get('roundNumber') == current_round]
                 if round_subs:
                     latest_sub = round_subs[0]

            needs_repair = False
            if not latest_sub:
                logger.warning(f"[SENTINEL] Missing submission for {model_name} in Round {current_round}.")
                needs_repair = True
            else:
                # Numerapi status check - this is a bit heuristic since API returns raw dicts
                # We often see 'status' or 'statusText'
                status = latest_sub.get('status', '').lower()
                if 'fail' in status or 'error' in status:
                    logger.error(f"[SENTINEL] Detected FAILED submission for {model_name}: {status}")
                    needs_repair = True
                else:
                    logger.info(f"[OK] {model_name} status: {status or 'Submitted'}")

            if needs_repair:
                repair_path = create_emergency_model(model_name)
                napi.model_upload(repair_path, model_id=model_id)
                logger.info(f"[SENTINEL] Emergency Repair Uploaded for {model_name}!")
                
        except Exception as e:
            logger.error(f"Sentinel error for {model_name}: {e}")

if __name__ == "__main__":
    check_and_repair()
