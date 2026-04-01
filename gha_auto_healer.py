import os
import sys
import json
import subprocess
import glob
from pathlib import Path

# Adhere to architecture rules
sys.path.append(r"C:\Users\admin\.antigravity\master")
try:
    from llm_router import route_task
except ImportError:
    route_task = None

FIX_MAP = {
    "Node.js 20 is deprecated": {
        "apply_fix": lambda log: add_node_env_vars(),
        "description": "Added Node 24 variables to mute Node deprecation warnings."
    },
    "The operation was canceled": {
        "apply_fix": lambda log: add_timeout_minutes(),
        "description": "Injected 60-min timeouts to identify true timeout hangs over silent cancellations."
    }
}

def add_node_env_vars():
    """Applies Node env vars to all YAML files in .github/workflows"""
    patched = False
    for yml in glob.glob(".github/workflows/*.yml"):
        with open(yml, "r", encoding='utf-8') as f:
            content = f.read()
        
        if "ACTIONS_RUNNER_FORCE_ACTIONS_NODE_VERSION" not in content and "env:" in content:
            new_content = content.replace("env:\n", "env:\n      ACTIONS_RUNNER_FORCE_ACTIONS_NODE_VERSION: \"node20\"\n      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: \"true\"\n")
            with open(yml, "w", encoding='utf-8') as f:
                f.write(new_content)
            patched = True
            print(f"Patched {yml} with Node.js env vars.")
    return patched

def add_timeout_minutes():
    """Applies timeout-minutes to jobs in all YAML files in .github/workflows"""
    patched = False
    for yml in glob.glob(".github/workflows/*.yml"):
        with open(yml, "r", encoding='utf-8') as f:
            content = f.read()
        
        if "timeout-minutes:" not in content and "runs-on: " in content:
            new_content = content.replace("runs-on: ubuntu-latest\n", "runs-on: ubuntu-latest\n    timeout-minutes: 60\n")
            with open(yml, "w", encoding='utf-8') as f:
                f.write(new_content)
            patched = True
            print(f"Patched {yml} with timeout-minutes.")
    return patched

def perform_deep_root_cause_analysis(run_id, log_tail):
    """Uses LLM to deeply analyze unknown failures and suggest code diffs."""
    print(f"Running LLM Deep Root Cause Analysis for run {run_id}...")
    if not route_task:
        print("[WARNING] LLM Router unavailable. Returning to heuristic map.")
        return False
        
    prompt = f"Analyze the following GitHub Action log and determine a root cause fix. Return ONLY Python code to patch the files directly, or a brief explanation if no patch is viable: {log_tail}"
    try:
        response = route_task("claude-3-5-sonnet", prompt, sys_prompt="You are an autonomous CI/CD auto-healer.", max_tokens=2000)
        return response.get("text", "No solution provided.")
    except Exception as e:
        print(f"Deep RCA Failure: {e}")
        return False

def push_fix(desc):
    """Commits and pushes the auto-heal directly to the repo."""
    subprocess.run(["git", "add", ".github/workflows/*.yml"], check=False)
    subprocess.run(["git", "commit", "-m", f"Auto-Heal: {desc} [skip ci]"], check=False)
    subprocess.run(["git", "push"], check=False)
    print("Fix pushed to repository!")

def check_failed_workflows():
    try:
        res = subprocess.run(["gh", "run", "list", "--status", "failure", "--json", "databaseId,name,headBranch"], capture_output=True, text=True, check=True)
        failed = json.loads(res.stdout)
    except Exception as e:
        print(f"Error fetching gh runs (is GH CLI authed?): {e}")
        return

    if not failed:
        print("No failed workflows detected. Ecosystem is healthy.")
        return
        
    for run in failed:
        run_id = run['databaseId']
        print(f"Investigating Run ID: {run_id} ({run['name']})...")
        
        # In a real environment, download with `gh run view <id> --log-failed`
        try:
            log_res = subprocess.run(["gh", "run", "view", str(run_id), "--log-failed"], capture_output=True, text=True)
            log_text = log_res.stdout
        except:
            log_text = ""
            
        fixed = False
        for pattern, config in FIX_MAP.items():
            if pattern in log_text:
                print(f"Detected known error pattern: {pattern}")
                if config["apply_fix"](log_text):
                    push_fix(config["description"])
                    fixed = True
                    break
                    
        if not fixed and log_text.strip():
            # Trigger Deep RCA
            analysis = perform_deep_root_cause_analysis(run_id, log_text[-2000:])
            print(f"RCA Result: {analysis}")
            
if __name__ == "__main__":
    check_failed_workflows()
