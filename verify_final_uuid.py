import sys
import os

# Set working directory to project root for internal imports
os.chdir(r'c:\Users\admin\Downloads\medsumag1\pcdraft')
sys.path.append('.')

from numerai_pipeline import _resolve_model_uuid

a0 = _resolve_model_uuid("anant0")
an = _resolve_model_uuid("ANANTA")
print(f"anant0 UUID: {a0}")
print(f"ANANTA UUID: {an}")
