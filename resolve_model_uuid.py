"""Resolve NumerAI model name -> UUID via GraphQL API."""
import requests
import json

def resolve_model_uuid(model_name: str) -> str:
    """Query NumerAI GraphQL to get model UUID from name."""
    url = "https://api-tournament.numer.ai"
    query = """
    query($modelName: String!) {
      v3UserProfile(modelName: $modelName) {
        id
        username
      }
    }
    """
    resp = requests.post(url, json={"query": query, "variables": {"modelName": model_name}})
    data = resp.json()
    print("Response:", json.dumps(data, indent=2))
    
    if "data" in data and data["data"].get("v3UserProfile"):
        return data["data"]["v3UserProfile"]["id"]
    
    # Fallback: try account-level query with auth
    import os, pathlib
    env_path = pathlib.Path(r"C:\Users\admin\.antigravity\master\.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    
    import numerapi
    pub = os.environ.get("NUMERAI_PUBLIC_ID", "")
    sec = os.environ.get("NUMERAI_SECRET_KEY", "")
    if pub and sec:
        napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
        # Try the account query
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
            print("Account query result:", json.dumps(result, indent=2, default=str))
            models = result.get("data", {}).get("account", {}).get("models", [])
            for m in models:
                if m.get("name") == model_name:
                    return m["id"]
        except Exception as e:
            print(f"Account query failed: {e}")
        
        # Try submission upload directly with model name
        # Some numerapi versions accept name directly
        try:
            # Check if get_account works
            print("Trying get_account...")
            # Just list the available methods
            methods = [m for m in dir(napi) if not m.startswith("_")]
            print("Available methods:", methods)
        except Exception as e:
            print(f"Method listing failed: {e}")
    
    return ""

if __name__ == "__main__":
    uuid = resolve_model_uuid("anant0")
    if uuid:
        print(f"\nMODEL UUID: {uuid}")
    else:
        print("\nCould not resolve UUID. Trying alternative approaches...")
