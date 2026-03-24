#!/usr/bin/env python3
import os
import sys
from pathlib import Path

MASTER_DIR = Path(r"C:\Users\admin\.antigravity\master")
sys.path.append(str(MASTER_DIR))
import llm_router

def test_all_apis():
    print("\n[ACTIVE API CONNECTIVITY AUDIT]")
    print("-" * 30)
    
    test_query = "Return only the word 'OK' if you see this."
    providers = ["gemini", "github", "groq", "openai", "claude"]
    
    for p in providers:
        try:
            print(f"Testing {p:10} ...", end="", flush=True)
            res = llm_router.route_query(
                system_prompt="Test",
                user_query=test_query,
                preferred_provider=p,
                max_retries=1
            )
            if "OK" in res['text'].upper():
                print(" [SUCCESS]")
            else:
                print(f" [FAILED] - Unexpected Response: {res['text'][:30]}")
        except Exception as e:
            print(f" [CRITICAL ERROR] - {str(e)[:50]}")

if __name__ == "__main__":
    test_all_apis()
