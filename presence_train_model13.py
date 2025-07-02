import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

data_dir = "./"
csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
all_data = []

print("[INFO] Loading and cleaning data...")

for file in csv_files:
    full_path = os.path.join(data_dir, file)
    try:
        df = pd.read_csv(full_path, skiprows=1, low_memory=False)
        print(f"[DEBUG] {file} → columns: {df.columns.tolist()}")

        time_col = next((col for col in df.columns if 'time' in col.lower()), None)
        if not time_col:
            print(f"[WARN] No time column found in {file}, skipping")
            continue

        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        df = df.dropna(subset=[time_col])
        df['timestamp'] = df[time_col]
        df['source_file'] = file

        # Clean and convert % strings
        for col in df.columns:
            if col not in ['timestamp', 'source_file', time_col]:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace('%', '', regex=False)
                    .str.strip()
                    .replace('', np.nan)
                    .astype(float)
                )

        all_data.append(df)

    except Exception as e:
        print(f"[ERROR] Failed to process {file}: {e}")

if not all_data:
    raise ValueError("No valid CSVs loaded.")

print(f"[INFO] Loaded {len(all_data)} files.")

# Combine all dataframes
combined_df = pd.concat(all_data, ignore_index=True)
combined_df = combined_df.sort_values(by="timestamp")

# Drop non-feature columns
feature_df = combined_df.drop(columns=["timestamp", "source_file"], errors='ignore')
feature_df = feature_df.dropna(axis=1, how='all')  # Drop columns with all NaNs

# Sliding window construction (length=24 for hourly → 1 day)
WINDOW_SIZE = 24
X = []

for col in feature_df.columns:
    series = feature_df[col].dropna().reset_index(drop=True)
    if len(series) < WINDOW_SIZE:
        continue
    for i in range(len(series) - WINDOW_SIZE + 1):
        window = series[i : i + WINDOW_SIZE].values
        if np.isnan(window).any():
            continue
        X.append(window)

if not X:
    raise ValueError("No valid sliding windows constructed from data.")

X = np.array(X)
print(f"[INFO] Training on {X.shape[0]} sliding windows, each of length {WINDOW_SIZE}.")

# Train Isolation Forest
model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
model.fit(X)

joblib.dump(model, "presence_model_final.pkl")
print("[✅] Model trained and saved to presence_model_final.pkl")

