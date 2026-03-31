import cloudpickle
import glob
from inspect import signature
import sys

with open('pkl_analysis.txt', 'w', encoding='utf-8') as out:
    for path in glob.glob('*.pkl'):
        out.write(f'Checking {path}...\n')
        try:
            with open(path, 'rb') as f:
                obj = cloudpickle.load(f)
            out.write(f'  Type: {type(obj)}\n')
            out.write(f'  Callable: {callable(obj)}\n')
            if callable(obj):
                out.write(f'  Signature: {signature(obj)}\n')
        except Exception as e:
            out.write(f'  Error: {e}\n')
