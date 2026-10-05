import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("Loading dataset...")
df = pd.read_csv('ml/data/raw/apachejit_total.csv')

print("\n========================================")
print(f"Total Commits:  {df.shape[0]:,}")
print(f"Total Features: {df.shape[1]}")
print("========================================")

print("\n[ Class Balance (Bug-Inducing vs Clean) ]")
print(df['fix'].value_counts())
print("\n[ Percentages ]")
print(df['fix'].value_counts(normalize=True).round(4) * 100)

print("\nGenerating skewness visualization...")
skewed_features = ['la', 'ld', 'nf'] 
fig, axes = plt.subplots(len(skewed_features), 2, figsize=(10, 8))

for i, col in enumerate(skewed_features):
    if col in df.columns:
        # Raw Data
        df[col].hist(bins=50, ax=axes[i, 0], color='#3498db', edgecolor='black')
        axes[i, 0].set_title(f"Raw '{col}' (Highly Skewed)")
        axes[i, 0].set_yscale('log')
        
        # Log-Transformed Data
        np.log1p(df[col]).hist(bins=50, ax=axes[i, 1], color='#e74c3c', edgecolor='black')
        axes[i, 1].set_title(f"Log1p '{col}' (Ready for ML)")

plt.tight_layout()
plt.savefig('ml/artifacts/data_skewness.png')
print("Success! Open ml/artifacts/data_skewness.png to see the plot.")