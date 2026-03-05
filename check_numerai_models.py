import os
import pathlib
import json
import logging

MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")

def _load_env() -> None:
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

def check_models():
    _load_env()
    try:
        import numerapi
    except ImportError:
        print("Error: numerapi not installed in this environment.")
        return

    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    if not pub or not sec:
        print("Error: NUMERAI_PUBLIC_ID or NUMERAI_SECRET_KEY not found in .env")
        return

    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
    
    models = napi.get_models()
    print(json.dumps(models, indent=2))

if __name__ == "__main__":
    check_models()
