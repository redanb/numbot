import numerapi
import json
import datetime

def default_handler(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def check():
    napi = numerapi.NumerAPI()
    target = "anant0"
    log_info = f"Checking public info for {target}..."
    print(log_info)
    
    try:
        # Check daily performances
        perf = napi.daily_model_performances(target)
        if perf:
            print(f"Latest Performance Date: {perf[0].get('date')}")
            print(f"Latest Corr: {perf[0].get('corr')}")
        else:
            print("No performance data found.")
            
        # Check leaderboard status for the model
        lb = napi.get_leaderboard(limit=1) # Just to see structure
        # Actually list_submissions is better if it exists
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
