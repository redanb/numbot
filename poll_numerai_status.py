import os, sys, time, logging, pathlib
import numerapi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [STATUS] %(message)s")
logger = logging.getLogger("NumerStatus")

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
    
    model_ids = {
        "anant0": "5fe67e13-8dae-4693-8294-84ddd8e8db80",
        "ananta": "14a8473a-b203-446e-a727-d55789c9cc81"
    }

    logger.info("--- Dashboard Status ---")
    for model_name, model_id in model_ids.items():
        try:
            subs = napi.submission_ids(model_id)
            if subs:
                latest = subs[0]
                status = latest.get('statusText') or latest.get('status') or "Unknown"
                round_num = latest.get('roundNumber', "???")
                logger.info(f"{model_name.upper():<8} | Round {round_num} | Status: {status}")
            else:
                logger.warning(f"{model_name.upper():<8} | No submissions found.")
        except Exception as e:
            logger.error(f"Error checking {model_name}: {e}")

if __name__ == "__main__":
    check_status()
