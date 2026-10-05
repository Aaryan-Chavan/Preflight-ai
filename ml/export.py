import pandas as pd
import numpy as np
import json
import os
import shap
from sklearn.isotonic import IsotonicRegression
from xgboost import XGBClassifier
import warnings

warnings.filterwarnings('ignore')

print("1. Training Production Model...")
df = pd.read_csv('ml/data/raw/apachejit_total.csv')
date_col = 'commit_date' if 'commit_date' in df.columns else 'date' if 'date' in df.columns else None
if date_col: df = df.sort_values(date_col)

y = df['fix'].astype(int)
cols_to_drop = ['fix', 'commit_hash', 'project', 'bug_id', '_id', 'name', 'date', 'commit_date', 'author_date']
X = df.drop(columns=[c for c in cols_to_drop if c in df.columns]).select_dtypes(include=[np.number])

skewed = ['la', 'ld', 'nf', 'nd', 'ns']
for col in skewed:
    if col in X.columns: X[col] = np.log1p(X[col])

n = len(df)
train_end, val_end = int(n * 0.7), int(n * 0.8)
X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

xgb = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, eval_metric='aucpr', random_state=42)
xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

print("2. Fitting Isotonic Calibration...")
# Calibrate using the validation set
val_probs = xgb.predict_proba(X_val)[:, 1]
iso = IsotonicRegression(out_of_bounds='clip')
iso.fit(val_probs, y_val)

print("3. Generating SHAP Explainer...")
# We use a background dataset for SHAP to compute expected values
explainer = shap.TreeExplainer(xgb, X_train.sample(100, random_state=42), feature_perturbation='interventional')

print("4. Exporting Artifacts...")
# Create product directories if they don't exist
out_dir = 'src/preflight/risk/models'
os.makedirs(out_dir, exist_ok=True)

# A. Save the XGBoost Model
xgb.save_model(os.path.join(out_dir, 'xgboost_model.json'))

# B. Save Calibration Curve (Allows np.interp in production without scikit-learn)
calib_data = {
    "x": iso.X_thresholds_.tolist(),
    "y": iso.y_thresholds_.tolist()
}
with open(os.path.join(out_dir, 'calibration.json'), 'w') as f:
    json.dump(calib_data, f, indent=2)

# C. Save Thresholds (Choosing roughly top 20% as High, next 30% as Medium)
# We calculate what calibrated probability corresponds to the 80th and 50th percentiles
test_probs_calibrated = iso.predict(xgb.predict_proba(X_test)[:, 1])
thresholds = {
    "HIGH": float(np.percentile(test_probs_calibrated, 80)),
    "MEDIUM": float(np.percentile(test_probs_calibrated, 50))
}
with open(os.path.join(out_dir, 'thresholds.json'), 'w') as f:
    json.dump(thresholds, f, indent=2)

# D. Save Feature Schema
schema = {
    "features": list(X_train.columns),
    "log1p_transforms": [col for col in skewed if col in X.columns]
}
with open(os.path.join(out_dir, 'feature_schema.json'), 'w') as f:
    json.dump(schema, f, indent=2)

print(f"Success! All production artifacts exported to {out_dir}/")