import pandas as pd
import numpy as np
import xgboost as xgb
import cloudpickle
from inspect import signature

model = xgb.XGBRegressor(max_depth=2)
model.fit(pd.DataFrame({'a':[1,2], 'b':[3,4]}), pd.Series([0,1]))

def my_predict(features: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(model.predict(features))

print('Callable:', callable(my_predict))
print('Signature:', signature(my_predict))
