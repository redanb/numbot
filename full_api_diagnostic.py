
import os
import sys
from pathlib import Path

# Load master for llm_router
sys.path.append(r"C:\Users\admin\.antigravity\master")
from llm_router import route_query, check_api_status

def diagnostic():
    print("--- API STATUS CHECK ---")
    status = check_api_status()
    for provider, info in status.items():
        print(f"Provider: {provider} | Key Set: {info['key_set']} | Priority: {info['priority']}")
    
    print("\n--- FUNCTIONAL TEST ---")
    test_query = "Return only the text 'API_WORKING' if you can read this."
    providers_to_test = ["gemini", "groq", "claude", "mistral", "xai", "perplexity", "openai"]
    
    for p in providers_to_test:
        if not status.get(p, {}).get('key_set'):
            print(f"Skipping {p} (No key)")
            continue
        try:
            print(f"Testing {p}...", end=" ", flush=True)
            res = route_query("System", test_query, preferred_provider=p, max_retries=1)
            text = res.get('text', '').strip()
            if 'API_WORKING' in text:
                print("PASSED")
            else:
                print(f"FAILED (Unexpected response: {text[:50]})")
        except Exception as e:
            print(f"ERROR: {str(e)[:100]}")

if __name__ == "__main__":
    diagnostic()
