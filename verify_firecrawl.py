"""
verify_firecrawl.py — Task Completion Gate (Article 3 Protocol)
Tests for the Firecrawl Agent + Parallel Runner global integration.
RULE-023: No emojis (Windows cp1252 safety).
"""
import sys
import os
import pathlib
import importlib.util
import time

# Windows stdout UTF-8 fix
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

MASTER_DIR = pathlib.Path(r"C:\Users\admin\.antigravity\master")
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


# --- Block 1: File existence ---
print("\n=== Block 1: File Existence ===")
files = [
    MASTER_DIR / "firecrawl_agent.py",
    MASTER_DIR / "parallel_runner.py",
    MASTER_DIR / "workflows" / "firecrawl.md",
    MASTER_DIR / "intel" / "scraped",
]
for f in files:
    check(f"EXISTS: {f.name}", f.exists(), str(f))

# --- Block 2: firecrawl_agent importable ---
print("\n=== Block 2: firecrawl_agent Module Structure ===")
spec = importlib.util.spec_from_file_location("firecrawl_agent", MASTER_DIR / "firecrawl_agent.py")
fc_mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(fc_mod)
    check("firecrawl_agent importable", True)
    check("firecrawl_agent has scrape()", hasattr(fc_mod, "scrape"))
    check("firecrawl_agent has crawl()", hasattr(fc_mod, "crawl"))
    check("firecrawl_agent has batch_scrape()", hasattr(fc_mod, "batch_scrape"))
except Exception as e:
    check("firecrawl_agent importable", False, str(e))

# --- Block 3: parallel_runner importable ---
print("\n=== Block 3: parallel_runner Module Structure ===")
spec2 = importlib.util.spec_from_file_location("parallel_runner", MASTER_DIR / "parallel_runner.py")
pr_mod = importlib.util.module_from_spec(spec2)
try:
    spec2.loader.exec_module(pr_mod)
    check("parallel_runner importable", True)
    check("parallel_runner has run_parallel()", hasattr(pr_mod, "run_parallel"))
    check("parallel_runner has run_from_config()", hasattr(pr_mod, "run_from_config"))
except Exception as e:
    check("parallel_runner importable", False, str(e))

# --- Block 4: Parallel execution speed test (no API required) ---
print("\n=== Block 4: Parallel Execution Speed Test ===")

def slow_task_a():
    time.sleep(0.5)
    return "result_a"

def slow_task_b():
    time.sleep(0.5)
    return "result_b"

def slow_task_c():
    time.sleep(0.5)
    return "result_c"

tasks = [
    {"name": "task_a", "fn": slow_task_a, "args": {}, "timeout": 10},
    {"name": "task_b", "fn": slow_task_b, "args": {}, "timeout": 10},
    {"name": "task_c", "fn": slow_task_c, "args": {}, "timeout": 10},
]

t_start   = time.perf_counter()
results   = pr_mod.run_parallel(tasks)
t_elapsed = time.perf_counter() - t_start

check("All 3 tasks returned ok", all(r["status"] == "ok" for r in results), str([r["status"] for r in results]))
check("Parallel speedup achieved", t_elapsed < 1.2, f"Wall time: {t_elapsed:.2f}s (sequential would be ~1.5s)")
check("Results list has 3 items", len(results) == 3, str(len(results)))

# --- Block 5: API key present ---
print("\n=== Block 5: API Key Configuration ===")
env_path = MASTER_DIR / ".env"
fc_key   = ""
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("FIRECRAWL_API_KEY="):
            fc_key = line.split("=", 1)[1].strip()
check("FIRECRAWL_API_KEY present in .env", bool(fc_key) and fc_key.startswith("fc-"), f"len={len(fc_key)}")

# --- Block 6: Shell interceptor wired ---
print("\n=== Block 6: Shell Interceptor Integration ===")
shell_text = (MASTER_DIR / "antigravity_shell.py").read_text(encoding="utf-8")
check("/scrape alias in shell interceptor",  "/scrape" in shell_text)
check("/crawl alias in shell interceptor",   "/crawl" in shell_text)
check("/run-parallel alias in shell interceptor", "/run-parallel" in shell_text)
check("FIRECRAWL key auto-loaded from .env", "FIRECRAWL_API_KEY" in shell_text)

# --- Block 7: Regression — existing features intact ---
print("\n=== Block 7: Regression Audit ===")
check("create video alias still present",    "create video" in shell_text)
check("SAST trigger still present",          "sast_triggers" in shell_text)
check("Hardcoded blocklist still present",   "HARDCODED_BLOCKLIST" in shell_text)
check("HITL threshold mechanism intact",     "hitl_risk_threshold" in shell_text)

# --- Summary ---
print(f"\n=== SUMMARY: {PASS} passed, {FAIL} failed ===")
if FAIL == 0:
    print("[PASS] verify_firecrawl.py: All checks passed. Firecrawl + Parallel Runner LIVE.")
    sys.exit(0)
else:
    print("[FAIL] verify_firecrawl.py: Some checks failed. Review above.")
    sys.exit(1)
