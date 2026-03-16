
import os
import sys
from pathlib import Path

# Load env manually
sys.path.append(r"C:\Users\admin\.antigravity\master")
from llm_router import _load_env_manually
_load_env_manually()

api_key = os.environ.get("XAI_API_KEY", "")
print(f"Key length: {len(api_key)}")
print(f"Starts with: {api_key[:10]}")
print(f"Ends with: {api_key[-10:]}")
print(f"Contains newline: {'\\n' in api_key}")
print(f"Contains space: {' ' in api_key}")

# Try to clean it
clean_key = api_key.replace('\n', '').replace('\r', '').strip()
print(f"Clean key length: {len(clean_key)}")
