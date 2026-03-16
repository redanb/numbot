import os
import requests
import json
from pathlib import Path

def test_api_auth():
    env_path = Path(r"C:\Users\admin\.antigravity\master\.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    email = os.getenv("BRAIN_EMAIL")
    password = os.getenv("BRAIN_PASSWORD")
    
    if not email or not password:
        print("Missing BRAIN_EMAIL or BRAIN_PASSWORD in .env")
        return

    base_url = "https://api.worldquantbrain.com"
    session = requests.Session()
    
    print(f"Testing Basic Auth for {email}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = session.post(
            f"{base_url}/authentication",
            auth=(email, password),
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 201:
            print("Auth Success! Session details:")
            print(session.cookies.get_dict())
            
            # Verify self endpoint
            resp = session.get(f"{base_url}/users/self")
            if resp.status_code == 200:
                print("Self endpoint verified successfully.")
            else:
                print(f"Self endpoint failed: {resp.status_code}")
                
        else:
            print(f"Auth Failed. Response Text:")
            print(response.text)
    except Exception as e:
        print(f"Exception during auth test: {e}")

if __name__ == "__main__":
    test_api_auth()
