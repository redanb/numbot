import os
import pathlib
import requests
import logging

MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")

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
        data = resp.json()
        if 'data' in data and data['data']['v3UserProfile']:
            return data['data']['v3UserProfile']['id']
        else:
            print(f"No result for {model_name}: {data}")
            return None
    except Exception as e:
        print(f"Error resolving {model_name}: {e}")
        return None

if __name__ == "__main__":
    _load_env()
    for m in ["anant0", "ANANTA"]:
        uuid = resolve_uuid(m)
        print(f"Model: {m} -> UUID: {uuid}")
