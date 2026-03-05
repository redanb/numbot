"""
verify_numerai_phase2.py — Task Completion Gate (Article 3 Protocol)
Tests for:
  - parallel_runner auto-wiring into digital_worker
  - numerai_pipeline module structure
  - cowork_scheduler NumerAI weekly task
  - MANUAL_TASKS.md updated with API key instructions
RULE-023: No emojis (Windows cp1252 safety).
"""
import sys
import pathlib
import importlib.util

sys.path.insert(0, str(pathlib.Path(r"C:\Users\admin\.antigravity\master")))

PCDRAFT = pathlib.Path(r"C:\Users\admin\Downloads\medsumag1\pcdraft")
MASTER  = pathlib.Path(r"C:\Users\admin\.antigravity\master")

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}" + (f" ({detail})" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" ({detail})" if detail else ""))


# === Block 1: File Existence ===
print("\n=== Block 1: File Existence ===")
files = [
    PCDRAFT / "numerai_pipeline.py",
    PCDRAFT / "numerai",                    # data directory
    PCDRAFT / "cowork_scheduler.py",
    MASTER / "parallel_runner.py",
]
for f in files:
    check(f"EXISTS: {f.name}", f.exists())

# === Block 2: numerai_pipeline module structure ===
print("\n=== Block 2: numerai_pipeline Module Structure ===")
spec = importlib.util.spec_from_file_location("numerai_pipeline", PCDRAFT / "numerai_pipeline.py")
napi_mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(napi_mod)
    check("numerai_pipeline importable", True)
    check("has download_data()",         hasattr(napi_mod, "download_data"))
    check("has engineer_features()",     hasattr(napi_mod, "engineer_features"))
    check("has train_model()",           hasattr(napi_mod, "train_model"))
    check("has generate_predictions()",  hasattr(napi_mod, "generate_predictions"))
    check("has submit_predictions()",    hasattr(napi_mod, "submit_predictions"))
    check("has run_full_pipeline()",     hasattr(napi_mod, "run_full_pipeline"))
except Exception as e:
    check("numerai_pipeline importable", False, str(e))

# === Block 3: digital_worker auto-parallel wiring ===
print("\n=== Block 3: digital_worker Auto-Parallel Integration ===")
dw_text = (PCDRAFT / "digital_worker.py").read_text(encoding="utf-8")
check("parallel_runner imported in digital_worker",  "from parallel_runner import run_parallel" in dw_text)
check("PARALLEL_RUNNER_AVAILABLE flag present",       "PARALLEL_RUNNER_AVAILABLE" in dw_text)
check("AUTO-PARALLEL tag in wave execution",          "AUTO-PARALLEL" in dw_text)
check("parallel dispatch logic present",              "_run_parallel_tasks" in dw_text)
check("sequential fallback present",                  "Sequential fallback" in dw_text.lower() or "sequential" in dw_text.lower())

# === Block 4: cowork_scheduler NumerAI weekly task ===
print("\n=== Block 4: cowork_scheduler NumerAI Weekly Task ===")
sched_text = (PCDRAFT / "cowork_scheduler.py").read_text(encoding="utf-8")
check("numerai_weekly task name present",    "numerai_weekly" in sched_text)
check("numerai_pipeline.py dispatch present","numerai_pipeline" in sched_text)
check("7-day scheduling present",            "days=7" in sched_text)

# === Block 5: MANUAL_TASKS.md updated ===
print("\n=== Block 5: MANUAL_TASKS.md Updated ===")
mt_text = (MASTER / "MANUAL_TASKS.md").read_text(encoding="utf-8")
check("NumerAI API key task in MANUAL_TASKS",    "NUMERAI_PUBLIC_ID" in mt_text)
check("NumerAI model creation step present",     "antigravity_quant" in mt_text)
check("Test run command present",                "numerai_pipeline.py --run" in mt_text)

# === Block 6: Dependencies available ===
print("\n=== Block 6: Python Dependencies ===")
for pkg in ["pandas", "xgboost", "scipy", "numerapi"]:
    try:
        importlib.import_module(pkg)
        check(f"{pkg} importable", True)
    except ImportError:
        check(f"{pkg} importable", False, "run: pip install " + pkg)

# === Block 7: Regression — existing shell aliases intact ===
print("\n=== Block 7: Regression Audit ===")
shell_text = (MASTER / "antigravity_shell.py").read_text(encoding="utf-8")
check("/scrape alias still present",       "/scrape" in shell_text)
check("/crawl alias still present",        "/crawl" in shell_text)
check("/run-parallel alias still present", "/run-parallel" in shell_text)
check("SAST scanner still wired",          "sast_triggers" in shell_text)
check("Blocklist still intact",            "HARDCODED_BLOCKLIST" in shell_text)

# === Summary ===
print(f"\n=== SUMMARY: {PASS} passed, {FAIL} failed ===")
if FAIL == 0:
    print("[PASS] verify_numerai_phase2.py: All checks passed.")
    sys.exit(0)
else:
    print("[FAIL] Some checks failed. Review above.")
    sys.exit(1)
