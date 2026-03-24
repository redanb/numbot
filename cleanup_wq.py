import shutil
import os
import stat
from pathlib import Path

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

targets = [
    Path(r"c:\Users\admin\Downloads\medsumag1\comp bet\brainbot"),
    Path(r"c:\Users\admin\Downloads\medsumag1\comp bet\check_worldquant_auth.py"),
    Path(r"c:\Users\admin\Downloads\medsumag1\comp bet\verify_task.py")
]

for target in targets:
    if target.exists():
        print(f"Deleting {target}...")
        if target.is_dir():
            shutil.rmtree(target, onerror=remove_readonly)
        else:
            os.remove(target)
        print(f"Deletion of {target} successful.")
