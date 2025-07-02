import pandas as pd
import joblib
import os

LEVEL_1 = 1440  # 24h
LEVEL_2 = 4320  # 72h
META_ALERT_THRESHOLD = 20  # shards

print("[INFO] Loading model...")
model = joblib.load("presence_model.pkl")

input_files = [f for f in os.listdir() if f.endswith(".csv")]

for file in input_files:
    print(f"\n[INFO] Loading {file}...")

    df = pd.read_csv(file, skiprows=1, low_memory=False)
    time_col = next((col for col in df.columns if 'time' in col.lower()), None)
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col])
    df['timestamp'] = df[time_col]

    numeric_df = df.select_dtypes(include="number")

    # Fill missing model features with 0s
    model_features = model.feature_names_in_
    missing = [col for col in model_features if col not in numeric_df.columns]
    if missing:
        print(f"[WARN] Missing columns in {file}: {missing}")
        for col in missing:
            numeric_df[col] = 0
    numeric_df = numeric_df[model_features]

    # ML model prediction
    print("[INFO] Running ML inference...")
    df["ml_anomaly"] = model.predict(numeric_df)

    # Static thresholds
    if "max_lag_minutes" in df.columns and "shard_id" in df.columns:
        df["breach_level"] = 0
        df.loc[df["max_lag_minutes"] > LEVEL_1, "breach_level"] = 1
        df.loc[df["max_lag_minutes"] > LEVEL_2, "breach_level"] = 2

        level1_count = (df["breach_level"] == 1).sum()
        level2_count = (df["breach_level"] == 2).sum()
        breached_shards = df[df["breach_level"] > 0]["shard_id"].nunique()

        print(f"[DEBUG] Threshold breaches in {file}:")
        print(f"  >24h (Level 1): {level1_count}")
        print(f"  >72h (Level 2): {level2_count}")
        print(f"  Unique shards breaching: {breached_shards}")

        if breached_shards >= META_ALERT_THRESHOLD:
            print("🚨 [META ALERT] ≥20 unique shards breached static thresholds")
    else:
        print("[WARN] Missing 'max_lag_minutes' or 'shard_id' — skipping static threshold checks.")

    # ML anomaly summary
    total_rows = len(df)
    anomaly_rows = (df["ml_anomaly"] == -1).sum()
    print(f"[INFO] ML anomaly rate: {anomaly_rows} / {total_rows} = {anomaly_rows / total_rows:.2%}")

    if anomaly_rows > 0:
        print("[INFO] Sample ML anomalies:")
        sample = df[df["ml_anomaly"] == -1].head(5)
        print(sample[["timestamp"] + list(numeric_df.columns[-5:])])

