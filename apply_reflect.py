import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(r"C:\Users\admin\.antigravity\master\learning_state.json")
RESUME_FILE = Path(r"C:\Users\admin\.antigravity\master\RESUME_CONTEXT.md")

new_rule = {
    "PREVENT_REPEAT": True,
    "correction_path": "Wrapped XGBRegressor instance cleanly inside a prediction function using closure capture instead of directly serializing the model object or buffering JSON bytearrays.",
    "rule": "MANDATORY NUMERAI PICKLING: Never use cloudpickle.dump(model) where model is an XGBRegressor object. Numerai's compute environment expects a function, e.g., cloudpickle.dump(predict_fn). Do NOT use bytearray loading for XGBoost models in the closure; capture the pre-loaded instance directly to avoid version serialization crashes.",
    "category": "Architecture / Cloud Pickle",
    "source_task": "Fix Numerai XGBRegressor Type Error"
}

if STATE_FILE.exists():
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError:
            state = {"permanent_rules": []}
else:
    state = {"permanent_rules": []}

if "permanent_rules" not in state:
    state["permanent_rules"] = []
state["permanent_rules"].append(new_rule)

with open(STATE_FILE, 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2)

if RESUME_FILE.exists():
    content = RESUME_FILE.read_text(encoding='utf-8')
    # Update execution status
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Execution Status:"):
            lines[i] = "Execution Status: 24/7 GOD-LEVEL AUTONOMOUS ALPHA FACTORY ACTIVE (Numerai Model Serialization FIXED)."
            break
    else:
        lines.insert(0, "Execution Status: 24/7 GOD-LEVEL AUTONOMOUS ALPHA FACTORY ACTIVE (Numerai Model Serialization FIXED).")
    
    # add progress
    lines.append("- FIXED: Numerai Compute TypeError 'XGBRegressor is not a callable object'.")
    lines.append("- FIXED: numerai_auto_upgrade.py now properly wraps models.")
    lines.append("- FIXED: emergency_r1223.py prediction closure uses direct model capture.")
    RESUME_FILE.write_text('\n'.join(lines), encoding='utf-8')

print('Reflect() completed.')
