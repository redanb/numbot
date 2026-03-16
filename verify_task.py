import sys
import os
import ast
from pathlib import Path

def test_cowork_scheduler():
    path = Path(r"c:\Users\admin\Downloads\medsumag1\pcdraft\cowork_scheduler.py")
    content = path.read_text(encoding="utf-8")
    assert "alpha_factory" in content, "alpha_factory missing from cowork_scheduler"
    assert "intelligence_orchestrator" in content, "Regression: intelligence_orchestrator missing from cowork_scheduler"
    # Parse to ensure syntax is valid
    ast.parse(content)
    print("SUCCESS: cowork_scheduler.py syntax and regression passed.")

def test_thinking_engine():
    path = Path(r"c:\Users\admin\Downloads\medsumag1\comp bet\brainbot\thinking_engine.py")
    content = path.read_text(encoding="utf-8")
    assert "get_latest_research" in content, "get_latest_research missing from thinking_engine"
    assert "analyze_history" in content, "Regression: analyze_history missing from thinking_engine"
    ast.parse(content)
    print("SUCCESS: thinking_engine.py syntax and regression passed.")

def test_evolution_tracker():
    path = Path(r"c:\Users\admin\Downloads\medsumag1\comp bet\brainbot\evolution_tracker.py")
    content = path.read_text(encoding="utf-8")
    assert "_auto_commit_log" in content, "auto_commit_log missing from evolution_tracker"
    assert "log_brain_submission" in content, "Regression: log_brain_submission missing from evolution_tracker"
    ast.parse(content)
    print("SUCCESS: evolution_tracker.py syntax and regression passed.")

if __name__ == "__main__":
    try:
        test_cowork_scheduler()
        test_thinking_engine()
        test_evolution_tracker()
        print("SUCCESS: ALL SINGULARITY MODULES VERIFIED")
        sys.exit(0)
    except Exception as e:
        print(f"FAILED: VERIFICATION FAILED: {e}")
        sys.exit(1)
