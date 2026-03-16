
import requests
import os
from pathlib import Path
import sys

# Load env manually
sys.path.append(r"C:\Users\admin\.antigravity\master")
from llm_router import _load_env_manually
_load_env_manually()

api_key = os.environ.get("XAI_API_KEY")
url = "https://api.x.ai/v1/models"
headers = {"Authorization": f"Bearer {api_key}"}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        models = response.json().get("data", [])
        print("Available XAI Models:")
        for m in models:
            print(f"- {m.get('id')}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception: {e}")
