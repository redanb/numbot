
import requests
import os
import sys
import json
from pathlib import Path

# Load env manually
sys.path.append(r"C:\Users\admin\.antigravity\master")
try:
    from llm_router import _load_env_manually
    _load_env_manually()
except ImportError:
    pass

def trigger_cloud_alpha_factory(universe="TOP3000"):
    """
    Triggers the GitHub Action workflow for Alpha Factory.
    Requires GITHUB_TOKEN to be set in .env or environment.
    """
    repo = "redanb/brainbot" # Based on git remote in brainbot folder
    workflow_id = "alpha_factory_cloud.yml"
    token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        print("[CLOUD] Error: GITHUB_TOKEN not found. Cannot delegate.")
        return False

    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "ref": "master",
        "inputs": {
            "target_universe": universe
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 204:
            print(f"[CLOUD] Successfully triggered {workflow_id} for universe {universe}")
            return True
        else:
            print(f"[CLOUD] Failed to trigger workflow: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[CLOUD] Exception during trigger: {e}")
        return False

if __name__ == "__main__":
    uni = sys.argv[1] if len(sys.argv) > 1 else "TOP3000"
    trigger_cloud_alpha_factory(uni)
