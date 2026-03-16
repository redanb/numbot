import numerapi
import json

def check_public_submissions():
    napi = numerapi.NumerAPI()
    query = """
    query($modelName: String!) {
      model(name: $modelName) {
        submissions {
          id
          round {
            number
          }
          status
        }
      }
    }
    """
    try:
        result = napi.raw_query(query, variables={"modelName": "anant0"})
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_public_submissions()
