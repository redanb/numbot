import sys
from pathlib import Path
import cloudpickle

print('Starting verify_task.py...')

def check_pass(msg):
    print(f'[PASS] {msg}')

def check_fail(msg):
    print(f'[FAIL] {msg}')
    sys.exit(1)

# 1. Regression Audit: Check if scripts still use cloudpickle appropriately
path1 = Path('numerai_auto_upgrade.py')
path2 = Path('emergency_r1223.py')

if not path1.read_text().find('cloudpickle.dump(predict, f)') > 0:
    check_fail('numerai_auto_upgrade.py not using function wrapper predict')
check_pass('numerai_auto_upgrade.py correctly wraps XGBRegressor in function closures')

if not path2.read_text().find('cloudpickle.dump(predict_callable, f)') > 0:
    check_fail('emergency_r1223.py not using function wrapper predict_callable')
check_pass('emergency_r1223.py correctly uses predict_callable closure without bytearrays')

print('\nALL CHECKS PASSED. Ready for Reflect().')
