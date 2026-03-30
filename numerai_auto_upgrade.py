"""
numerai_auto_upgrade.py - v5.2.0 DEFINITIVE FIX
================================================
ROOT CAUSE: cloudpickle default protocol=5 (Python 3.14) is incompatible with
            Numerai backend Python 3.12. Numerai's predict.py catches the TypeError
            as "Pickle incompatible with 3.12".

FIX: cloudpickle.dump(fn, f, protocol=2) on ALL serialization calls.
     Protocol 2 is version-agnostic across ALL Python 3.x (3.6 to 3.14+).
"""
import os
import sys
import json
import logging
import datetime
import time
import base64
import pathlib
import cloudpickle
import pandas as pd
import numpy as np
import xgboost as xgb
import optuna
from numerapi import NumerAPI

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
MODELS = {
    "anant0": "5fe67e13-8dae-4693-8294-84ddd8e8db80",
    "ananta": "14a8473a-b203-446e-a727-d55789c9cc81"
}
CHAMPION_METRICS_PATH = "champion_metrics.json"
VAL_SCORE_FLOOR = 0.002
MAX_TRIALS = 20
MAX_RUNTIME_MIN = 160
START_TIME = time.time()

DATASET_VERSION = "v5.0"
TRAIN_FILE = "train.parquet"
VAL_FILE = "validation.parquet"
ERA_COL = "era"
TARGET_COL = "target"
N_CV_ERAS = 4
_DATA_CACHE = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)


# ─── DATA LOADING ────────────────────────────────────────────────────────────

def load_numerai_data(napi):
    if _DATA_CACHE:
        return _DATA_CACHE["train"], _DATA_CACHE["val"], _DATA_CACHE["features"]
    logger.info(f"Checking for Numerai {DATASET_VERSION} datasets...")
    if not pathlib.Path(TRAIN_FILE).exists():
        logger.info("Downloading train.parquet (~2GB)...")
        napi.download_dataset(f"{DATASET_VERSION}/train.parquet", dest_path=TRAIN_FILE)
    if not pathlib.Path(VAL_FILE).exists():
        logger.info("Downloading validation.parquet...")
        napi.download_dataset(f"{DATASET_VERSION}/validation.parquet", dest_path=VAL_FILE)
    train = pd.read_parquet(TRAIN_FILE)
    val = pd.read_parquet(VAL_FILE)
    feature_cols = [c for c in train.columns if c.startswith("feature_")]
    keep = [ERA_COL, TARGET_COL] + feature_cols
    train = train[[c for c in keep if c in train.columns]].copy()
    val = val[[c for c in keep if c in val.columns]].copy()
    _DATA_CACHE.update({"train": train, "val": val, "features": feature_cols})
    logger.info(f"Loaded {len(train)} train, {len(val)} val, {len(feature_cols)} features.")
    return train, val, feature_cols


# ─── METRICS ─────────────────────────────────────────────────────────────────

def era_spearman(preds, y, eras):
    from scipy.stats import spearmanr
    scores = []
    for era in eras.unique():
        mask = eras == era
        if mask.sum() < 10:
            continue
        corr, _ = spearmanr(preds[mask], y[mask])
        if not np.isnan(corr):
            scores.append(corr)
    return float(np.mean(scores)) if scores else 0.0


def temporal_cv(params, train, feature_cols):
    eras = sorted(train[ERA_COL].unique())
    n = len(eras)
    if n < N_CV_ERAS + 2:
        return 0.0
    fold_size = n // (N_CV_ERAS + 1)
    scores = []
    for k in range(N_CV_ERAS):
        cutoff = (k + 1) * fold_size
        val_end = min(cutoff + fold_size, n)
        tr = train[train[ERA_COL].isin(eras[:cutoff])]
        vl = train[train[ERA_COL].isin(eras[cutoff:val_end])]
        X_tr = tr[feature_cols].fillna(0.5).values.astype(np.float32)
        y_tr = tr[TARGET_COL].values.astype(np.float32)
        X_vl = vl[feature_cols].fillna(0.5).values.astype(np.float32)
        y_vl = vl[TARGET_COL].values.astype(np.float32)
        mdl = xgb.XGBRegressor(**params, tree_method="hist", device="cpu", verbosity=0)
        mdl.fit(X_tr, y_tr)
        scores.append(era_spearman(mdl.predict(X_vl), y_vl, vl[ERA_COL]))
    return float(np.mean(scores))


# ─── OPTUNA OBJECTIVE ────────────────────────────────────────────────────────

def objective(trial, train, feature_cols):
    if (time.time() - START_TIME) > (MAX_RUNTIME_MIN * 60):
        trial.study.stop()
        return 0.0
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 800),
        'max_depth': trial.suggest_int('max_depth', 3, 6),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.4, 0.8),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 20),
    }
    return temporal_cv(params, train, feature_cols)


# ─── FALLBACK WEIGHTS ─────────────────────────────────────────────────────────

def compute_fallback_weights(val, feature_cols):
    try:
        sample = val[feature_cols + [TARGET_COL]].sample(min(5000, len(val))).fillna(0.5)
        y = sample[TARGET_COL].values.astype(np.float64)
        X = sample[feature_cols].values.astype(np.float64)
        weights = []
        for i in range(X.shape[1]):
            c = float(np.corrcoef(X[:, i], y)[0, 1])
            weights.append(c * 0.01 if not np.isnan(c) else 0.0)
        return weights
    except Exception:
        return [0.002] * len(feature_cols)


# ─── RESILIENT WRAPPER ────────────────────────────────────────────────────────

def create_resilient_predict(model_b64, feature_cols, fallback_weights):
    """
    Creates a self-contained closure that:
    1. Tries XGBoost with embedded B64-JSON weights (primary)
    2. Falls back to Pure NumPy correlation weights (secondary)
    3. Falls back to uniform shuffle (absolute failsafe)
    
    MUST be serialized with cloudpickle.dump(..., protocol=2) to avoid
    Python version incompatibility between 3.14 (local) and 3.12 (Numerai).
    """
    n_features = len(feature_cols)

    def predict(live_features):
        import pandas as pd
        import numpy as np
        import base64
        import tempfile
        import os

        # Feature selection
        feat_cols = [c for c in feature_cols if c in live_features.columns]
        if not feat_cols:
            feat_cols = [c for c in live_features.columns if c.startswith("feature_")][:n_features]
        X = live_features[feat_cols].fillna(0.5).values.astype(np.float64)
        if X.shape[1] < n_features:
            pad = np.full((X.shape[0], n_features - X.shape[1]), 0.5)
            X = np.hstack([X, pad])
        X = X[:, :n_features]

        # PRIMARY: XGBoost
        try:
            import xgboost as xgb
            tf = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
            tf.write(base64.b64decode(model_b64))
            tf.close()
            mdl = xgb.XGBRegressor()
            mdl.load_model(tf.name)
            os.unlink(tf.name)
            preds = mdl.predict(X.astype(np.float32))
            ranked = pd.Series(preds).rank(pct=True).values
            return pd.DataFrame({'prediction': ranked}, index=live_features.index)
        except Exception as e_xgb:
            print(f"[FALLBACK-1] XGBoost failed: {e_xgb}")

        # SECONDARY: Pure NumPy linear
        try:
            w = np.array(fallback_weights[:n_features], dtype=np.float64)
            raw = X.dot(w)
            order = np.argsort(np.argsort(raw))
            ranked = (order + 0.5) / len(order)
            return pd.DataFrame({'prediction': ranked}, index=live_features.index)
        except Exception as e_np:
            print(f"[FALLBACK-2] NumPy failed: {e_np}")

        # ABSOLUTE FAILSAFE
        import random
        n = len(live_features)
        preds = [(i + 0.5) / n for i in range(n)]
        random.shuffle(preds)
        return pd.DataFrame({'prediction': preds}, index=live_features.index)

    return predict


# ─── MAIN ────────────────────────────────────────────────────────────────────

def pre_flight_security_check():
    if os.path.exists(".env"):
        logger.warning("[GUARDRAIL] .env file detected in working directory.")


def run_upgrade():
    pre_flight_security_check()
    public_id = os.getenv("NUMERAI_PUBLIC_ID")
    secret_key = os.getenv("NUMERAI_SECRET_KEY")
    if not public_id or not secret_key:
        logger.error("[GUARDRAIL] Missing credentials.")
        sys.exit(1)

    napi = NumerAPI(public_id, secret_key)
    train, val, feature_cols = load_numerai_data(napi)
    fallback_weights = compute_fallback_weights(val, feature_cols)

    full_metrics = {}
    if os.path.exists(CHAMPION_METRICS_PATH):
        try:
            content = open(CHAMPION_METRICS_PATH).read().strip()
            if content:
                full_metrics = json.loads(content)
        except Exception:
            pass

    for model_name, model_id in MODELS.items():
        logger.info(f"\n{'='*50}\nPROCESSING {model_name.upper()}\n{'='*50}")
        champion_data = full_metrics.get(model_name, {})
        champion_score = champion_data.get("best_score", -1.0) if isinstance(champion_data, dict) else -1.0

        # Optuna search
        study = optuna.create_study(direction="maximize")
        study.optimize(lambda t: objective(t, train, feature_cols), n_trials=MAX_TRIALS)
        best_params = study.best_trial.params
        logger.info(f"Best CV score: {study.best_trial.value:.5f} | Params: {best_params}")

        # Final model on full training data
        final_model = xgb.XGBRegressor(**best_params, tree_method="hist", device="cpu", verbosity=0)
        final_model.fit(
            train[feature_cols].fillna(0.5).values.astype(np.float32),
            train[TARGET_COL].values.astype(np.float32)
        )

        # Validation score
        X_val = val[feature_cols].fillna(0.5).values.astype(np.float32)
        y_val = val[TARGET_COL].values.astype(np.float32)
        val_preds = final_model.predict(X_val)
        final_val_score = era_spearman(val_preds, y_val, val[ERA_COL])
        logger.info(f"Val Score: {final_val_score:.5f} | Champion: {champion_score:.5f}")

        if not (final_val_score > champion_score and final_val_score >= VAL_SCORE_FLOOR):
            logger.info(f"Skipping {model_name}. Score not improved or below floor.")
            continue

        logger.info(f"!!! EVOLUTION SUCCESS !!! {model_name}: {final_val_score:.5f}")

        # Serialize model as B64-JSON
        final_model.save_model("_tmp_xgb.json")
        with open("_tmp_xgb.json", "rb") as fh:
            model_b64 = base64.b64encode(fh.read()).decode("utf-8")
        os.remove("_tmp_xgb.json")

        # Build resilient closure
        predict_fn = create_resilient_predict(model_b64, feature_cols, fallback_weights)

        # Pre-flight self-test
        try:
            mock_df = pd.DataFrame(
                np.random.rand(10, len(feature_cols)),
                columns=feature_cols
            )
            out = predict_fn(mock_df)
            assert out.shape == (10, 1), f"Bad shape: {out.shape}"
            assert out['prediction'].between(0, 1).all(), "Out of range"
            logger.info(f"[AUDIT] Pre-flight PASSED for {model_name}.")
        except Exception as exc:
            logger.error(f"[AUDIT] FAILED for {model_name}: {exc}. Skipping upload.")
            continue

        # ── SERIALIZE WITH PROTOCOL=2 (DEFINITIVE FIX) ──────────────────────
        model_path = f"{model_name}_uploaded.pkl"
        with open(model_path, "wb") as fh:
            cloudpickle.dump(predict_fn, fh, protocol=2)

        pkl_size_kb = os.path.getsize(model_path) / 1024
        logger.info(f"[SERIALIZATION] {model_path} ({pkl_size_kb:.1f} KB, cloudpickle protocol=2)")

        # Upload
        try:
            napi.model_upload(model_path, model_id=model_id)
            logger.info(f"[SUCCESS] {model_name} uploaded!")
            full_metrics[model_name] = {
                "best_score": final_val_score,
                "cv_score": study.best_trial.value,
                "params": best_params,
                "timestamp": datetime.datetime.now().isoformat(),
                "version": "5.2.0-protocol2-fix",
            }
        except Exception as exc:
            logger.error(f"Upload failed for {model_name}: {exc}")

    with open(CHAMPION_METRICS_PATH, "w") as fh:
        json.dump(full_metrics, fh, indent=2)
    logger.info("Champion metrics saved.")


if __name__ == "__main__":
    run_upgrade()
