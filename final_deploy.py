import numerapi
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("DEPLOY")

MASTER_DIR = Path(r"C:\Users\admin\.antigravity\master")

def load_env():
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

def deploy():
    load_env()
    napi = numerapi.NumerAPI(
        public_id=os.environ.get("NUMERAI_PUBLIC_ID"),
        secret_key=os.environ.get("NUMERAI_SECRET_KEY")
    )
    
    model_id = "5fe67e13-8dae-4693-8294-84ddd8e8db80" # anant0
    pkl_path = r"C:\Users\admin\Downloads\medsumag1\pcdraft\numerai\models\callable_r1221_20260312_044219.pkl"
    
    log.info(f"Targeting model {model_id} with file {pkl_path}")
    
    if not Path(pkl_path).exists():
        log.error("PKL file not found!")
        return

    log.info("Uploading standardized model (2-arg predict signature)...")
    try:
        napi.model_upload(pkl_path, model_id=model_id)
        log.info("SUCCESS: Model uploaded.")
    except Exception as e:
        log.error(f"Upload failed: {e}")

if __name__ == "__main__":
    deploy()
