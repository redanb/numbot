"""
fix_and_submit_r1221.py
Emergency fix for Round 1221:
  1. Re-trains model (callable wrapper)
  2. Uploads new callable PKL to Numerai Compute
  3. Submits predictions via CSV (direct upload)

Run: python fix_and_submit_r1221.py
"""
import sys
import os
import pathlib
import logging
import datetime
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FIX] %(levelname)s %(message)s")
log = logging.getLogger("r1221_fix")

# ─── Add pipeline dir to path ───────────────────────────────────────────────────
SCRIPT_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from numerai_pipeline import (
    _load_env, _get_numerai_keys, download_data, train_model,
    generate_predictions, submit_predictions, upload_model,
    MODEL_DIR, DATA_DIR, OUTPUT_DIR
)

def main():
    log.info("=" * 60)
    log.info("EMERGENCY FIX: Round 1221 Submission Recovery")
    log.info("=" * 60)
    
    _load_env()
    
    # Step 1: Download fresh live data
    log.info("[STEP 1] Downloading latest live data...")
    try:
        download_data()
        log.info("[STEP 1] OK")
    except Exception as e:
        log.error("[STEP 1] FAILED: %s", e)
        return

    # Step 2: Train and get callable wrapper
    log.info("[STEP 2] Training model (will return callable)...")
    try:
        model_callable, features = train_model()
        log.info("[STEP 2] OK - model is callable: %s", callable(model_callable))
    except Exception as e:
        log.error("[STEP 2] FAILED: %s", e)
        return

    # Step 3: Generate predictions CSV
    log.info("[STEP 3] Generating predictions...")
    try:
        preds_path = generate_predictions(model_callable, features)
        log.info("[STEP 3] OK - saved to %s", preds_path)
    except Exception as e:
        log.error("[STEP 3] FAILED: %s", e)
        return

    # Step 4: Submit predictions CSV for ANANT0 (direct submission)
    log.info("[STEP 4] Submitting CSV predictions for ANANT0...")
    try:
        result = submit_predictions(preds_path, model_name="anant0")
        log.info("[STEP 4] anant0 result: %s", result)
    except Exception as e:
        log.error("[STEP 4] FAILED: %s", e)

    # Step 5: Upload new callable PKL to Numerai Compute
    log.info("[STEP 5] Uploading new callable PKL to Numerai Compute...")
    try:
        model_files = sorted(MODEL_DIR.glob("xgb_model_*.pkl"))
        if not model_files:
            log.error("[STEP 5] No PKL found in %s", MODEL_DIR)
            return
        latest_pkl = model_files[-1]
        log.info("[STEP 5] Using PKL: %s", latest_pkl)
        
        # Verify it's callable before uploading
        import cloudpickle
        with open(latest_pkl, "rb") as f:
            obj = cloudpickle.load(f)
        log.info("[STEP 5] Loaded object callable: %s (type=%s)", callable(obj), type(obj).__name__)
        if not callable(obj):
            log.error("[STEP 5] ABORT - pickled object is NOT callable. Will not upload.")
            return
            
        result = upload_model(latest_pkl, model_name="anant0")
        log.info("[STEP 5] Upload result: %s", result)
    except Exception as e:
        log.error("[STEP 5] FAILED: %s", e)

    log.info("=" * 60)
    log.info("FIX COMPLETE. Check Numerai dashboard in ~5 min for submission status.")
    log.info("=" * 60)

if __name__ == "__main__":
    main()
