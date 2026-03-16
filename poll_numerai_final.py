import os, sys, logging, pathlib
import numerapi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [POLL] %(message)s")
log = logging.getLogger()

MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")

def load_env():
    env_path = MASTER_DIR / ".env"
    log.info(f"Looking for .env at: {env_path}")
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val
    
    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    if pub and sec:
        log.info(f"API Keys found. PUB: {pub[:5]}... SEC: {sec[:5]}...")
    else:
        log.error("API Keys MISSING in environment.")

def poll():
    load_env()
    napi = numerapi.NumerAPI(
        public_id=os.environ.get("NUMERAI_PUBLIC_ID"),
        secret_key=os.environ.get("NUMERAI_SECRET_KEY")
    )
    
    log.info("Fetching models status for account...")
    try:
        models = napi.get_models()
        # models is a dict mapping name to id
        log.info(f"Models in account: {models}")
        
        target_model = "anant0"
        model_id = models.get(target_model)
        
        if not model_id:
            log.error(f"Model {target_model} not found in account models.")
            return

        # Use raw_query for submission status but carefully
        # Actually, let's try getting the latest submission via a simpler query
        # or check round_model_performances
        
        log.info(f"Checking submissions for {target_model} (ID: {model_id})...")
        
        # napi.submission_ids returns a list of IDs
        subs = napi.submission_ids(model_id=model_id)
        if not subs:
            log.info(f"No submission IDs found for {target_model}.")
            return
            
        latest_sub_id = subs[0]
        log.info(f"Latest Submission ID: {latest_sub_id}")
        
        # Now get details of this submission
        # We can use a simpler query for a single submission
        query = """
        query($id: String!) {
          submissions(id: $id) {
            id
            filename
            status
            round {
              number
            }
          }
        }
        """
        res = napi.raw_query(query, variables={"id": latest_sub_id})
        sub_details = res["data"]["submissions"][0]
        
        log.info(f"Status for {target_model}: {sub_details['status']}")
        
        if sub_details['status'].lower() in ["failed", "crash"]:
            log.error(f"RESULT: FAIL - Round {sub_details['round']['number']} {target_model} failed.")
        elif sub_details['status'].lower() in ["success", "passed", "complete"]:
            log.info(f"RESULT: PASS - Round {sub_details['round']['number']} {target_model} is good!")
        else:
            log.info(f"RESULT: {sub_details['status'].upper()} - Round {sub_details['round']['number']} still working.")

    except Exception as e:
        log.error(f"Failed to poll Numerai: {e}")

if __name__ == "__main__":
    poll()
