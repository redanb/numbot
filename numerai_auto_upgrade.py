"""
numerai_auto_upgrade.py
24/7 Cloud Engine for anant0 using Optuna and GitHub Actions.
"""
import os
import sys
import json
import random
import logging
import datetime
import pathlib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import KFold
import cloudpickle
import numexpr as ne

# Force sys.path to find our modules in pcdraft
PCDRAFT_DIR = r"C:\Users\admin\Downloads\medsumag1\pcdraft"
if PCDRAFT_DIR not in sys.path:
    sys.path.insert(0, PCDRAFT_DIR)

try:
    from numerai_pipeline import (
        download_data, engineer_features, _get_numerai_keys, _load_env,
        DATA_DIR, OUTPUT_DIR
    )
    from numerai_model_upload import create_predict_function
except ImportError as e:
    print(f"Failed to import from pcdraft: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AUTO-UPGRADE] %(levelname)s %(message)s")
logger = logging.getLogger("auto_upgrade")

CHAMPION_FILE = pathlib.Path(__file__).parent / "champion_metrics.json"

def get_champion_score():
    if CHAMPION_FILE.exists():
        try:
            with open(CHAMPION_FILE, "r") as f:
                data = json.load(f)
                return data.get("best_cv_spearman", 0.0)
        except Exception as e:
            logger.warning("Failed to read champion file: %s", e)
    return 0.0100  # Default baseline if no file exists

def save_champion_score(score, params):
    try:
        with open(CHAMPION_FILE, "w") as f:
            json.dump({
                "best_cv_spearman": score,
                "params": params,
                "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
            }, f, indent=2)
        logger.info("Saved new champion score: %.4f", score)
    except Exception as e:
        logger.error("Failed to save champion file: %s", e)

def load_and_prep_data():
    """Load a randomized slice of data to fit in GitHub Actions RAM limit."""
    import pyarrow.parquet as pq
    train_path = DATA_DIR / "train.parquet"
    if not train_path.exists():
        logger.info("Downloading data...")
        download_data()

    logger.info("Loading feature metadata...")
    schema = pq.read_schema(train_path)
    all_cols = schema.names
    
    # Select subset of features (e.g., first 50) for speed/RAM
    feature_cols = [c for c in all_cols if c.startswith("feature_")][:50]
    target_cols  = [c for c in all_cols if "target" in c]
    target_col   = target_cols[0] if target_cols else "target"
    era_col      = "era"
    load_cols    = [era_col] + feature_cols + [target_col]

    logger.info("Reading parquet, %d features...", len(feature_cols))
    df = pd.read_parquet(train_path, columns=load_cols)
    
    # Use day-of-year as a rotating seed to cycle through the dataset
    doy = datetime.datetime.utcnow().timetuple().tm_yday
    logger.info("Sampling 10%% data with rotational seed %d", doy)
    df = df.sample(frac=0.10, random_state=doy).copy()

    for col in feature_cols + [target_col]:
        df[col] = df[col].astype(np.float32)

    logger.info("Engineering features. This may take a minute...")
    df = engineer_features(df, feature_cols)
    
    eng_cols = [c for c in df.columns if c.startswith("zscore_")] + \
               [c for c in df.columns if c.startswith("regime_")] + \
               [c for c in df.columns if c.startswith("sizing_")] + \
               ["market_regime"]
    all_features = feature_cols + [c for c in eng_cols if c in df.columns]
    
    return df, all_features, target_col, era_col

def run_optuna_study(df, features, target_col, era_col, n_trials=10):
    try:
        import optuna
    except ImportError:
        logger.error("Please run: pip install optuna")
        sys.exit(1)
        
    eras = df[era_col].unique()
    
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 400, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 0.9),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.3, 0.9),
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": 0
        }
        
        kf = KFold(n_splits=3, shuffle=True, random_state=42)
        cv_scores = []
        
        for train_idx, val_idx in kf.split(eras):
            train_eras = eras[train_idx]
            val_eras   = eras[val_idx]
            
            # Use boolean masking for faster filtering
            train_mask = df[era_col].isin(train_eras)
            val_mask   = df[era_col].isin(val_eras)
            
            X_tr = df.loc[train_mask, features].fillna(0).values
            y_tr = df.loc[train_mask, target_col].values
            X_vl = df.loc[val_mask, features].fillna(0).values
            y_vl = df.loc[val_mask, target_col].values
            
            mdl = xgb.XGBRegressor(**params)
            mdl.fit(X_tr, y_tr, verbose=False)
            
            preds = mdl.predict(X_vl)
            
            # Speedy spearmanr
            from scipy.stats import spearmanr
            score, _ = spearmanr(preds, y_vl)
            cv_scores.append(score)
            
        return np.mean(cv_scores)

    # Make optuna silent to avoid log spam
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize")
    logger.info("Starting Optuna hunt for %d trials...", n_trials)
    study.optimize(objective, n_trials=n_trials)
    
    logger.info("Optuna Best Trial Score: %.4f", study.best_value)
    return study.best_value, study.best_params

def upload_new_champion(df, features, target_col, params):
    """Train on full sampled data and upload to NumerAI."""
    logger.info("Retraining final model on selected hyperparams...")
    X_full = df[features].fillna(0).values
    y_full = df[target_col].values

    final_model = xgb.XGBRegressor(**params)
    final_model.fit(X_full, y_full, verbose=False)

    predict_fn = create_predict_function(final_model, features)
    UPLOAD_PATH = pathlib.Path("anant0_auto_uploaded.pkl")
    
    with open(UPLOAD_PATH, "wb") as f:
        cloudpickle.dump(predict_fn, f)
        
    _load_env()
    import numerapi
    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    if not pub or not sec:
        logger.error("Missing NumerAI API keys, cannot upload.")
        return
        
    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
    model_id = "5fe67e13-8dae-4693-8294-84ddd8e8db80"  # anant0
    
    try:
        sub_id = napi.model_upload(str(UPLOAD_PATH), model_id=model_id)
        logger.info("Successfully uploaded new Champion! Sub ID: %s", sub_id)
    except Exception as e:
        logger.error("NumerAPI Upload Failed: %s", e)

def main():
    champion_score = get_champion_score()
    logger.info("Current Champion CV Score: %.4f", champion_score)
    
    df, features, target_col, era_col = load_and_prep_data()
    
    # We run fewer trials locally for testing, but chron will run ~30
    n_trials = int(os.environ.get("OPTUNA_TRIALS", "15"))
    candidate_score, candidate_params = run_optuna_study(df, features, target_col, era_col, n_trials=n_trials)
    
    if candidate_score > champion_score * 1.01:
        logger.info("[VICTORY] Challenger (%.4f) beat Champion (%.4f)! Commencing upgrade.", candidate_score, champion_score)
        upload_new_champion(df, features, target_col, candidate_params)
        save_champion_score(candidate_score, candidate_params)
        
        # We append a success tag to a GITHUB_OUTPUT file if available to signal a commit is needed
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"champion_updated=true\n")
                f.write(f"new_score={candidate_score:.4f}\n")
    else:
        logger.info("[DEFEAT] Challenger (%.4f) failed to beat Champion (%.4f). Retaining baseline.", candidate_score, champion_score)
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("champion_updated=false\n")

if __name__ == "__main__":
    main()
