
import os
import sys
from pathlib import Path

# Load master for llm_router
sys.path.append(r"C:\Users\admin\.antigravity\master")
import llm_router

def diagnostic():
    print("--- ISOLATED API TEST (Direct Calls) ---")
    _load = getattr(llm_router, '_load_env_manually', None)
    if _load: _load()
    
    test_query = "Return only the text 'API_WORKING' if you can read this."
    system_prompt = "You are a tester."
    
    providers = {
        "gemini": llm_router._call_gemini,
        "groq": llm_router._call_groq,
        "claude": llm_router._call_claude,
        "openai": llm_router._call_openai,
        "xai": llm_router._call_xai,
        "perplexity": llm_router._call_perplexity,
        "mistral": llm_router._call_mistral
    }
    
    for name, func in providers.items():
        print(f"Testing {name:10s}...", end=" ", flush=True)
        try:
            # Gemini needs specialized key handling in the router but the direct call takes it in kwargs
            # or uses os.environ if we are lucky.
            # In llm_router.py, _call_gemini uses kwargs.get("api_key")
            key = os.environ.get(f"{name.upper()}_API_KEY")
            if name == "claude": key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                print("MISSING KEY")
                continue
                
            if name == "gemini":
                res = func(system_prompt, test_query, api_key=key)
            else:
                res = func(system_prompt, test_query)
            
            text = res.get('text', '').strip()
            if 'API_WORKING' in text:
                print("PASSED")
            else:
                print(f"FAILED (Unexpected response: {text[:50]})")
        except Exception as e:
            err = str(e)
            if "exhausted" in err.lower() or "429" in err or "quota" in err.lower():
                print("EXHAUSTED (Quota/Rate Limit)")
            elif "not found" in err.lower() or "400" in err:
                print(f"CONFIG ERROR (Model/Arg Not Found): {err[:60]}")
            else:
                print(f"ERROR: {err[:80]}")

if __name__ == "__main__":
    diagnostic()
