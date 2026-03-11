import os
import pathlib
import requests
import logging
from numerapi import NumerAPI

# Configure logging to console only (no cp1252 issues)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [EMERGENCY] %(message)s")
logger = logging.getLogger("emergency_submit")

MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")
PREDICTIONS_FILE = pathlib.Path(r"C:\Users\admin\Downloads\medsumag1\pcdraft\numerai\predictions\predictions_20260305_134514.csv")

def _load_env():
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

def resolve_uuid(model_name):
    query = """query($n: String!){v3UserProfile(modelName: $n){id}}"""
    url = "https://api-tournament.numer.ai"
    try:
        resp = requests.post(url, json={'query': query, 'variables': {'n': model_name}}, timeout=15)
        return resp.json()['data']['v3UserProfile']['id']
    except Exception as e:
        logger.error(f"Failed to resolve {model_name}: {e}")
        return None

def emergency_submit():
    _load_env()
    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    
    if not pub or not sec:
        logger.error("API keys not found in .env")
        return

    napi = NumerAPI(public_id=pub, secret_key=sec)
    
    models = ["anant0", "ANANTA"]
    for model in models:
        uuid = resolve_uuid(model)
        if not uuid:
            continue
            
        logger.info(f"Submitting to {model} (UUID: {uuid})...")
        try:
            # We avoid napi.get_models() which requires read_user_info
            # upload_predictions only requires 'upload_submissions' scope
            sub_id = napi.upload_predictions(str(PREDICTIONS_FILE), model_id=uuid)
            logger.info(f"SUCCESS: {model} -> Submission ID: {sub_id}")
        except Exception as e:
            logger.error(f"FAILED to submit to {model}: {e}")

if __name__ == "__main__":
    emergency_submit()
