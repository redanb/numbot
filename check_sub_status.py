import os
import numerapi
import datetime
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("checker")

def check_current_status():
    MASTER_DIR = Path(r"C:\Users\admin\.antigravity\master")
    env_path = MASTER_DIR / ".env"
    pub = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec = os.environ.get("NUMERAI_SECRET_KEY", "")
    
    if env_path.exists() and not (pub and sec):
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                if "NUMERAI_PUBLIC_ID" in key: pub = val.strip()
                if "NUMERAI_SECRET_KEY" in key: sec = val.strip()

    if not pub or not sec:
        logger.error("Keys missing")
        return

    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
    
    current_round = napi.get_current_round()
    logger.info(f"Current Round: {current_round}")
    
    models = ["anant0", "ananta"]
    for model in models:
        # get_submissions returns list of submissions for the model
        subs = napi.get_submissions(model_id=None) # Passing None might default to primary or we need the model-specific ID
        # Better: use get_models to get {name: id} then filter
        model_map = napi.get_models()
        m_id = model_map.get(model)
        
        if not m_id:
             logger.warning(f"Model {model} not found")
             continue
             
        model_subs = napi.get_submissions(model_id=m_id)
        
        # Check if any submission matches current round
        round_subRows = [s for s in model_subs if s.get('roundNumber') == current_round]
        
        if round_subRows:
            logger.info(f"Model {model} has {len(round_subRows)} submissions for round {current_round}.")
        else:
            logger.info(f"Model {model} HAS NO SUBMISSIONS for round {current_round}. TRIGGER NEEDED.")

if __name__ == "__main__":
    check_current_status()
