import pandas as pd
import numpy as np
import xgboost as xgb
import cloudpickle
from scipy.stats import rankdata

# Dummy training
X = pd.DataFrame(np.random.rand(100, 5), columns=[f"feature_{i}" for i in range(5)])
y = pd.Series(np.random.rand(100))

model = xgb.XGBRegressor(n_estimators=10, max_depth=3)
model.fit(X, y)

# Save booster to bytes
booster = model.get_booster()
raw_bytes = booster.save_raw("ubj")  # Universal Binary JSON format
feature_cols = list(X.columns)

def predict_fn(live_data: pd.DataFrame) -> pd.Series:
    import pandas as pd
    import numpy as np
    import xgboost as xgb
    from scipy.stats import rankdata

    # Reconstruct booster
    b = xgb.Booster()
    b.load_model(bytearray(raw_bytes))
    
    avail = [c for c in feature_cols if c in live_data.columns]
    X_live = live_data[avail].fillna(0).astype(np.float32)
    
    # DMatrix for booster
    dtest = xgb.DMatrix(X_live)
    preds = b.predict(dtest)
    
    # Rank-normalize
    ranked = (rankdata(preds) - 0.5) / len(preds)
    return pd.Series(ranked, index=live_data.index, name="prediction")

# Pickle it
with open("test_predict.pkl", "wb") as f:
    cloudpickle.dump(predict_fn, f)

# Unpickle and test
with open("test_predict.pkl", "rb") as f:
    loaded_fn = cloudpickle.load(f)

test_df = pd.DataFrame(np.random.rand(10, 5), columns=[f"feature_{i}" for i in range(5)])
res = loaded_fn(test_df)
print("SUCCESS!")
print(res.head())
