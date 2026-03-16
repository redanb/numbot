import json
import os
import datetime

STATE_FILE = r"C:\Users\admin\.antigravity\master\learning_state.json"

new_rule_1 = {
    "id": "RULE-083",
    "date_learned": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
    "source_task": "Global System Workflows",
    "error": "Agent doing same work repeatedly because memory is not pre-loaded aggressively.",
    "rule": "ALWAYS GATHER CONTEXT: At the onset of any task, you must parse learning_state and RESUME_CONTEXT. Refer to workflows/gather_context.md. Never assume clean execution on a complex project without contextual reading.",
    "category": "workflow_automation",
    "PREVENT_REPEAT": True,
    "correction_path": "Created workflows/gather_context.md that forces explicit file reads."
}

new_rule_2 = {
    "id": "RULE-084",
    "date_learned": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
    "source_task": "Numerai Predict Segfault",
    "error": "Segmentation fault caused by XGBoost allocating too many threads (n_jobs=-1) inside the heavily constrained Numerai/Fargate compute container, and reading mutable bytearrays.",
    "rule": "NUMERAI COMPUTE XGB THREADING: ALWAYS explicitly force single-threaded execution (b.set_param({'nthread': 1})) when initializing an XGBoost Booster for Numerai Compute. Ensure raw booster bytes are cast as immutable bytes() to prevent C pointer memory violations.",
    "category": "system_stability",
    "PREVENT_REPEAT": True,
    "correction_path": "Added b.set_param({'nthread': 1}) and cast bytearray to bytes() before initialization."
}

with open(STATE_FILE, "r", encoding="utf-8") as f:
    state = json.load(f)

state["permanent_rules"].append(new_rule_1)
state["permanent_rules"].append(new_rule_2)
state["last_updated"] = datetime.datetime.utcnow().isoformat()

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2)

print("Reflect() applied RULE-083 and RULE-084 successfully.")
