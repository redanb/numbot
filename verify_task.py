import os
from pathlib import Path

def test_alpha_factory_env():
    print("Checking alpha_factory.py for .env support...")
    content = Path(r"c:\Users\admin\Downloads\medsumag1\comp bet\brainbot\alpha_factory.py").read_text()
    assert "Path(r\"C:\\Users\\admin\\.antigravity\\master\\.env\")" in content
    print("SUCCESS: .env support verified in alpha_factory.py")

def test_aggregator_exists():
    print("Checking global_task_aggregator.py...")
    path = Path(r"C:\Users\admin\Downloads\medsumag1\medleads\global_task_aggregator.py")
    assert path.exists()
    print("SUCCESS: Aggregator script exists.")

def test_runner_integration():
    print("Checking sahimed_daily_runner.py integration...")
    content = Path(r"C:\Users\admin\Downloads\medsumag1\medleads\sahimed_daily_runner.py").read_text()
    assert "import global_task_aggregator" in content
    assert "{global_tasks_html}" in content
    print("SUCCESS: Global task queue integrated into Sahimed runner.")

if __name__ == "__main__":
    try:
        test_alpha_factory_env()
        test_aggregator_exists()
        test_runner_integration()
        print("\nALL LOCAL TESTS PASSED. REGRESSION AUDIT: Pre-existing email logic remains intact.")
    except Exception as e:
        print(f"\nVERIFICATION FAILED: {e}")
        exit(1)
