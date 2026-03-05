import os
import pathlib
import sys

def verify():
    print("=== Numerai Automation Verification Suite ===")
    
    # 1. Dependency Check
    try:
        import cloudpickle
        print("[PASS] cloudpickle is installed.")
    except ImportError:
        print("[FAIL] cloudpickle is NOT installed.")
        sys.exit(1)

    # 2. File Check
    scripts = [
        r"C:\Users\admin\Downloads\medsumag1\comp bet\numerai_model_upload.py",
        r"C:\Users\admin\Downloads\medsumag1\pcdraft\numerai_pipeline.py"
    ]
    for s in scripts:
        if pathlib.Path(s).exists():
            print(f"[PASS] Script exists: {os.path.basename(s)}")
        else:
            print(f"[FAIL] Script MISSING: {s}")
            sys.exit(1)

    # 3. Artifact Check
    uploaded_pkl = r"C:\Users\admin\Downloads\medsumag1\pcdraft\numerai\models\anant0_uploaded.pkl"
    if pathlib.Path(uploaded_pkl).exists():
        print(f"[PASS] Uploaded model .pkl exists: {os.path.basename(uploaded_pkl)}")
    else:
        print(f"[FAIL] Uploaded model .pkl MISSING: {uploaded_pkl}")
        sys.exit(1)

    # 4. Regression Audit: Verify local scheduler still exists
    scheduler = r"C:\Users\admin\Downloads\medsumag1\pcdraft\cowork_scheduler.py"
    if pathlib.Path(scheduler).exists():
        print("[PASS] Regression Audit: Local scheduler remains intact.")
    else:
        print("[FAIL] Regression Audit: Local scheduler MISSING.")
        sys.exit(1)

    print("\n[SUCCESS] All verification steps passed.")
    sys.exit(0)

if __name__ == "__main__":
    verify()
