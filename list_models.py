import os
import pathlib
import json
import numerapi

MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")

def _load_env():
    env_path = MASTER_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

def get_all_models():
    _load_env()
    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    
    if not pub or not sec:
        print("API keys not found")
        return

    napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
    
    account_query = """
    query {
      account {
        models {
          id
          name
          tournament
        }
      }
    }
    """
    try:
        result = napi.raw_query(account_query, authorization=True)
        models = result.get("data", {}).get("account", {}).get("models", [])
        print(f"Total models found: {len(models)}")
        for m in models:
            print(f"Model Name: {m['name']}, UUID: {m['id']}, Tournament: {m['tournament']}")
    except Exception as e:
        print(f"Account query failed: {e}")

if __name__ == "__main__":
    get_all_models()
