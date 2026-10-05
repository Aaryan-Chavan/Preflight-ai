import pandas as pd
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
import warnings

# Suppress minor scikit-learn warnings for cleaner output
warnings.filterwarnings('ignore')

print("Loading and preparing data...")
df = pd.read_csv('ml/data/raw/apachejit_total.csv')

# 1. Sort Chronologically (Crucial for Step 3: Time-Based Split)
date_col = 'commit_date' if 'commit_date' in df.columns else 'date' if 'date' in df.columns else None
if date_col:
    df = df.sort_values(date_col)

# 2. Separate Features (X) and Target (y)
y = df['fix'].astype(int)

# Drop non-predictive metadata strings so we only feed math to the models
cols_to_drop = ['fix', 'commit_hash', 'project', 'bug_id', '_id', 'name', 'date', 'commit_date', 'author_date']
X = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
X = X.select_dtypes(include=[np.number]) # Keep only numeric columns

# Apply log1p to highly skewed size features (Step 2 optimization)
skewed = ['la', 'ld', 'nf', 'nd', 'ns']
for col in skewed:
    if col in X.columns:
        X[col] = np.log1p(X[col])

# 3. Time-Based Split: 70% Train, 10% Validation, 20% Test
n = len(df)
train_end = int(n * 0.7)
val_end = int(n * 0.8)

X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

print(f"Split complete: Train={len(X_train):,}, Val={len(X_val):,}, Test={len(X_test):,}\n")

# Evaluation Helper
def evaluate(model_name, y_true, y_pred_proba):
    pr_auc = average_precision_score(y_true, y_pred_proba)
    roc_auc = roc_auc_score(y_true, y_pred_proba)
    print(f"{model_name:22s} | PR-AUC: {pr_auc:.3f} | ROC-AUC: {roc_auc:.3f}")

print("--- Step 4: Baselines ---")

# Baseline A: The "Guess Safe" model (Majority Class)
dummy = DummyClassifier(strategy='prior')
dummy.fit(X_train, y_train)
evaluate("1. Majority Class", y_test, dummy.predict_proba(X_test)[:, 1])

# Baseline B: The "Bigger is Riskier" simple heuristic
if 'la' in X_test.columns:
    # Normalize lines added ('la') between 0 and 1 to act as a fake probability
    rule_proba = X_test['la'] / X_test['la'].max()
    evaluate("2. Rule: Lines Added", y_test, rule_proba)

# Baseline C: Standard Logistic Regression
lr = LogisticRegression(max_iter=1000)
lr.fit(X_train, y_train)
evaluate("3. Logistic Regression", y_test, lr.predict_proba(X_test)[:, 1])

print("\n--- Step 5: The Primary Model ---")

# Train XGBoost
xgb = XGBClassifier(
    n_estimators=100, 
    max_depth=4,
    learning_rate=0.1,
    eval_metric='aucpr',
    early_stopping_rounds=10,
    random_state=42
)

# Use validation set to prevent overfitting
xgb.fit(
    X_train, y_train, 
    eval_set=[(X_val, y_val)], 
    verbose=False
)
evaluate("4. XGBoost", y_test, xgb.predict_proba(X_test)[:, 1])