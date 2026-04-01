import sys
import os
from pathlib import Path

print('Starting verify_task.py...')

def check_pass(msg):
    print(f'[PASS] {msg}')

def check_fail(msg):
    print(f'[FAIL] {msg}')
    sys.exit(1)

# 1. Regression Audit: Check if scripts still use cloudpickle appropriately
path1 = Path('numerai_auto_upgrade.py')
path2 = Path('emergency_r1223.py')

if path1.exists() and not path1.read_text().find('cloudpickle.dump(predict_fn, fh, protocol=2)') > 0:
    check_fail('numerai_auto_upgrade.py not using function wrapper predict')
if path1.exists(): check_pass('numerai_auto_upgrade.py correctly wraps XGBRegressor in function closures')

if path2.exists() and not path2.read_text().find('cloudpickle.dump(predict_callable, f)') > 0:
    check_fail('emergency_r1223.py not using function wrapper predict_callable')
if path2.exists(): check_pass('emergency_r1223.py correctly uses predict_callable closure without bytearrays')

# 2. New Checks: Global Healer & YML Rules
healer_path = Path('gha_auto_healer.py')
if not healer_path.exists():
    check_fail('gha_auto_healer.py is missing.')
if 'add_node_env_vars' not in healer_path.read_text():
    check_fail('gha_auto_healer.py is missing node env mapping logic.')
check_pass('gha_auto_healer.py logic is sound.')

yml_path = Path('.github/workflows/numerai_auto_upgrade.yml')
if not yml_path.exists():
    check_fail('numerai_auto_upgrade.yml is missing.')
yml_text = yml_path.read_text()
if 'ACTIONS_RUNNER_FORCE_ACTIONS_NODE_VERSION: "node20"' not in yml_text:
    check_fail('numerai_auto_upgrade.yml is missing Node 20 runner fallback')
if 'timeout-minutes: 60' not in yml_text:
    check_fail('numerai_auto_upgrade.yml is missing timeout-minutes')
check_pass('numerai_auto_upgrade.yml has Node 20 backward compatibility and timeouts injected.')

healer_yml_path = Path('.github/workflows/global_ecosystem_healer.yml')
if not healer_yml_path.exists():
    check_fail('global_ecosystem_healer.yml is missing.')
check_pass('global_ecosystem_healer.yml exists.')

print('\nALL CHECKS PASSED. Ready for Reflect().')
