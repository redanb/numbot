import os
import sys
import pathlib
from datetime import datetime

# Paths
MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")
COMP_BET_DIR = pathlib.Path(r"c:\Users\admin\Downloads\medsumag1\comp bet")
BRAINBOT_DIR = COMP_BET_DIR / "brainbot"

def _load_env():
    potential_paths = [
        MASTER_DIR / ".env",
        COMP_BET_DIR / ".env",
        BRAINBOT_DIR / ".env",
        pathlib.Path.cwd() / ".env"
    ]
    for env_path in potential_paths:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    val = val.strip().strip("'").strip('"')
                    os.environ[key.strip()] = val

def get_numerai_status():
    """Fetches the latest Numerai round status for ANANT0 and ANANTA."""
    _load_env()
    import numerapi
    pub = os.environ.get("NUMERAI_PUBLIC_ID")
    sec = os.environ.get("NUMERAI_SECRET_KEY")
    if not pub or not sec:
        return "Numerai: Credentials Missing — NUMERAI_PUBLIC_ID or NUMERAI_SECRET_KEY not found in .env"
    
    try:
        napi = numerapi.NumerAPI(public_id=pub, secret_key=sec)
        models = {
            "anant0": "5fe67e13-8dae-4693-8294-84ddd8e8db80",
            "ANANTA": "14a8473a-b203-446e-a727-d55789c9cc81"
        }
        status_lines = []
        for name, mid in models.items():
            query = """query($modelId: String!) {
                model(modelId: $modelId) {
                    name
                    submissions {
                        id
                        round { number openTime }
                        selected
                        status
                    }
                }
            }"""
            res = napi.raw_query(query, variables={"modelId": mid})
            model_data = res.get("data", {}).get("model")
            if model_data:
                subs = model_data.get("submissions")
                if subs:
                    latest = subs[0]
                    rnd = latest['round']
                    open_time = rnd.get('openTime', '')[:10] if rnd.get('openTime') else ''
                    status_lines.append(
                        f"  📊 {name}: Round {rnd['number']} | Date: {open_time} | Status: {latest['status']}"
                    )
                else:
                    status_lines.append(f"  {name}: No submissions found")
            else:
                status_lines.append(f"  {name}: Failed to fetch data")
        return "\n".join(status_lines)
    except Exception as e:
        return f"  Numerai Error: {e}"

def get_evolution_report():
    """Pull the full evolution tracker report."""
    try:
        sys.path.insert(0, str(BRAINBOT_DIR))
        from evolution_tracker import get_evolution_report as _get_report
        return _get_report()
    except Exception as e:
        return f"Evolution Tracker Error: {e}"

def get_wqb_status():
    """Checks the local evolution log for last Brain session."""
    try:
        import json
        log_path = MASTER_DIR / "evolution_log.json"
        if log_path.exists():
            data = json.loads(log_path.read_text(encoding="utf-8"))
            entries = data.get("brain", [])
            if entries:
                last = entries[-1]
                return (
                    f"  Last Session: {last.get('date', '?')}\n"
                    f"  Alpha ID: {last.get('alpha_id', '?')}\n"
                    f"  Sharpe: {last.get('sharpe', '?')} | Fitness: {last.get('fitness', '?')} | Turnover: {last.get('turnover', '?')}\n"
                    f"  Status: {last.get('status', '?')}\n"
                    f"  Expression: {last.get('expression', '?')[:80]}..."
                )
            else:
                return "  No Brain submissions logged yet (Evolution Tracker just initialized)."
        return "  Running every 6h via GitHub Actions (5 workers). Log not yet populated."
    except Exception as e:
        return f"  Brain Status Error: {e}"

def get_pulse_status():
    """Checks if real-time Telegram notifications are active."""
    token_path = MASTER_DIR / "automated_skills" / ".telegram_token"
    if token_path.exists():
        return "  🟢 Active: Real-Time Telegram Pulse (HITL-Approved)"
    return "  🔴 Inactive: Telegram Token Missing"

def aggregate_report():
    now = datetime.now().strftime('%Y-%m-%d %H:%M IST')
    report_lines = [
        f"        🔱 SAHIMED MASTER OPS MAIL - {now} 🔱",
        "="*60,
        "System Pulse & Frequency",
        "-"*30,
        f"  Submission Interval: 4 Hours (Bursts at 00, 04, 08, 12, 16 UTC)",
        f"  Daily Frequency: 5x Daily Operations",
        get_pulse_status(),
        "",
        "NUMERAI INTELLIGENCE (Round 1223)",
        "-"*30,
        get_numerai_status(),
        "",
        "WORLDQUANT BRAIN ALPHA FACTORY",
        "-"*30,
        get_wqb_status(),
        "",
        get_evolution_report(),
        "="*60,
        "SECURITY GATES: Permission Protocol v1.0 ACTIVE",
        "GWS INTEGRATION: PAUSED (Awaiting HITL Approval)"
    ]
    return "\n".join(report_lines)

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(aggregate_report())
