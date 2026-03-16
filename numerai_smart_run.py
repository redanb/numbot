import os
import sys
import json
import logging
import datetime
import pathlib
import numerapi
from pathlib import Path

# Reuse logic from emergency_r1223.py for training/prediction
# but add smart check at the start.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NUMERAI_SMART] %(levelname)s %(message)s"
)
logger = logging.getLogger("smart_runner")

MASTER_DIR = Path(r"C:\Users\admin\.antigravity\master")
COMP_BET_DIR = Path(r"c:\Users\admin\Downloads\medsumag1\comp bet")

def get_keys():
    env_path = MASTER_DIR / ".env"
    pub = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec = os.environ.get("NUMERAI_SECRET_KEY", "")
    if env_path.exists() and not (pub and sec):
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                if "NUMERAI_PUBLIC_ID" in key: pub = val.strip()
                if "NUMERAI_SECRET_KEY" in key: sec = val.strip()
    return pub, sec

def check_if_run_needed(napi, model_name, current_round):
    """Check if model has already submitted for this round."""
    model_map = napi.get_models()
    model_id = model_map.get(model_name)
    if not model_id:
        logger.warning(f"Model {model_name} not found.")
        return True # Run anyway just in case
    
    # submission_ids returns a list of {roundNumber, submissionId, ...}
    # However, sometimes it returns just IDs or needs model_id
    try:
        # Based on numerapi v2.x+
        subs = napi.submission_ids(model_id=model_id)
        # subs is likely a list of {round: ID} map or a dictionary
        # Let's be safe and check all sources
        for sub in subs:
             if sub.get('roundNumber') == current_round:
                 logger.info(f"Model {model_name} already submitted for Round {current_round}. (SubID: {sub.get('id')})")
                 return False
    except Exception as e:
        logger.error(f"Error checking submissions for {model_name}: {e}")
        return True # Default to run if error

    return True

def main():
    pub, sec = get_keys()
    if not pub or not sec:
        logger.error("API Keys missing. Cannot automate.")
        return

    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
    current_round = napi.get_current_round()
    logger.info(f"Current Numerai Round: {current_round}")

    models = ["anant0", "ananta"]
    needs_run = False
    for m in models:
        if check_if_run_needed(napi, m, current_round):
            logger.info(f"Model {m} needs submission for {current_round}.")
            needs_run = True
        else:
            logger.info(f"Model {m} is UP TO DATE.")

    if needs_run:
        logger.info("Executing Emergency Run pipeline for Round %s", current_round)
        # We trigger the existing robust emergency_r1223.py script
        # but we need to ensure it's round-generic if possible, 
        # or we just keep using it as the standard for 1223+.
        import subprocess
        emergency_script = COMP_BET_DIR / "emergency_r1223.py"
        try:
            subprocess.run([sys.executable, str(emergency_script)], check=True)
            logger.info("Pipeline completed successfully.")
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
    else:
        logger.info("No submission required today.")

if __name__ == "__main__":
    main()
