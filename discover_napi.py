import numerapi
import os

def discover():
    napi = numerapi.NumerAPI()
    methods = [m for m in dir(napi) if not m.startswith("_")]
    print("Available methods in NumerAPI:")
    for m in methods:
        print(f" - {m}")
    
    # Try common candidates
    candidates = ["get_submissions", "list_submissions", "get_model_submissions", "get_user"]
    for c in candidates:
        if hasattr(napi, c):
            print(f"\nFOUND CANDIDATE: {c}")

if __name__ == "__main__":
    discover()
