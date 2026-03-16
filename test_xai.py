
import os
import sys
from pathlib import Path

# Add master to path
sys.path.append(r"C:\Users\admin\.antigravity\master")
from llm_router import _call_xai, _load_env_manually

_load_env_manually()
print(f"XAI_API_KEY set: {bool(os.environ.get('XAI_API_KEY'))}")

try:
    res = _call_xai("You are a helpful assistant.", "Hello, are you Grok?")
    print(f"Result: {res['text'][:100]}...")
except Exception as e:
    print(f"Error: {e}")
