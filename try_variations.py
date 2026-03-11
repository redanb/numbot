import requests

def resolve_uuid(model_name):
    query = """query($n: String!){v3UserProfile(modelName: $n){id}}"""
    url = "https://api-tournament.numer.ai"
    try:
        resp = requests.post(url, json={'query': query, 'variables': {'n': model_name}}, timeout=15)
        data = resp.json()
        if 'data' in data and data['data']['v3UserProfile']:
            return data['data']['v3UserProfile']['id']
    except:
        pass
    return None

if __name__ == "__main__":
    for m in ["ANANTA", "ananta", "Ananta", "ANANTA_1", "ananta_0"]:
        uuid = resolve_uuid(m)
        if uuid:
            print(f"FOUND: {m} -> {uuid}")
        else:
            print(f"FAILED: {m}")
