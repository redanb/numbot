import os, sys, time, logging, pathlib
import numerapi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [STATUS] %(message)s")
log = logging.getLogger()

MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")

def load_env():
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), val)

def check_status():
    load_env()
    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
    
    # Models to check
    models = ["anant0", "ananta"]
    model_ids = {
        "anant0": "5fe67e13-8dae-4693-8294-84ddd8e8db80",
        "ananta": "c2006764-670d-4054-998f-a9cb59670162" # Example placeholder if needed
    }

    log.info("Checking submission status on Numerai Site...")
    
    for model_name, model_id in model_ids.items():
        try:
            # Get latest submissions
            submissions = napi.get_submissions(model_id=model_id)
            if not submissions:
                log.info(f"Model {model_name}: No submissions found.")
                continue
            
            latest = submissions[0]
            log.info(f"Model {model_name} (Round {latest['roundNumber']}):")
            log.info(f"  Status: {latest['status']}")
            log.info(f"  Created: {latest['timestamp']}")
            log.info(f"  Validation Score: {latest.get('validationScore')}")
            
            # Check for logs if failed
            if latest['status'].lower() == "failed":
                log.error(f"  Submission FAILED. Check site logs for {model_name}.")
            elif latest['status'].lower() == "passed":
                log.info(f"  Submission PASSED.")
            else:
                log.info(f"  Submission is {latest['status']}...")

        except Exception as e:
            log.error(f"Error checking {model_name}: {e}")

if __name__ == "__main__":
    check_status()
