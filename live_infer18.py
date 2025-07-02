import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import joblib

# === Config ===
GRAFANA_API_KEY = "API TOKEN"
GRAFANA_GRAPHITE_URL = "GRAPHITE_URL"
MODEL_PATH = "presence_model_final.pkl"
HOURS_BACK = 24
MACHINES = [f"n{i}-primary-meraki-com" for i in range(200, 300)]
AGGREGATORS = [
    "ProbeTablesAggregator.network_tag_node_tag_cmx_probe_counts_by_ssid_day_utc",
    "ProbeTablesAggregator.network_tag_node_tag_cmx_probe_counts_by_ssid_hour_utc",
    "ProbeTablesAggregator.network_tag_node_tag_cmx_probe_hll_hour",
    "ProbeTablesAggregator.node_tag_cmx_probe_counts_by_ssid_day_utc",
    "ProbeTablesAggregator.node_tag_cmx_probe_counts_by_ssid_hour_utc",
    "ProbeTablesAggregator.node_tag_cmx_probe_hll_hour"
]

HEADERS = { "Authorization": f"Bearer {GRAFANA_API_KEY}" }

# === Load model ===
print(f"[INFO] Loading model from {MODEL_PATH}...")
model = joblib.load(MODEL_PATH)
window_size = model.n_features_in_
print(f"[INFO] Model expects input of length {window_size}")

# === Time bounds ===
now = datetime.utcnow()
from_ts = int((now - timedelta(hours=HOURS_BACK)).timestamp())
until_ts = int(now.timestamp())

def query_series(machine, aggregator):
    graphite_target = f"statsd.{machine}.gauges.aggregator.agg_length_behind_ratio.{aggregator}"
    params = {
        "target": graphite_target,
        "from": from_ts,
        "until": until_ts,
        "format": "json"
    }
    try:
        r = requests.get(GRAFANA_GRAPHITE_URL, headers=HEADERS, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"[WARN] Failed for {machine} / {aggregator} — HTTP {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Timeout or connection error for {machine} / {aggregator}: {e}")
    return None

def clean_percent_values(datapoints):
    # In case values are percent strings like '0.01%' convert to float
    cleaned = []
    for val in datapoints:
        if isinstance(val, str) and val.endswith("%"):
            try:
                cleaned.append(float(val.strip('%')) / 100)
            except:
                cleaned.append(None)
        else:
            cleaned.append(val)
    return [v for v in cleaned if v is not None]

def detect_anomaly_for_series(series_data, machine, aggregator):
    if not series_data:
        return None
    for series in series_data:
        raw_values = [v[0] for v in series["datapoints"] if v[0] is not None]
        values = clean_percent_values(raw_values)
        if len(values) < window_size:
            continue
        X = pd.DataFrame([values[-window_size:]], columns=[f"t-{i}" for i in range(window_size)])
        pred = model.predict(X)[0]
        if pred == -1:
            return {
                "machine": machine,
                "aggregator": aggregator,
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "high"
            }
    return None

# === Anomaly Detection ===
anomalies = []
for machine in MACHINES:
    for aggregator in AGGREGATORS:
        print(f"[INFO] Querying {machine} / {aggregator}...")
        data = query_series(machine, aggregator)
        result = detect_anomaly_for_series(data, machine, aggregator)
        if result:
            print(f"[ANOMALY] {result}")
            anomalies.append(result)

# === Save output ===
out_json = "live_anomalies.json"
with open(out_json, "w") as f:
    json.dump(anomalies, f, indent=2)
print(f"[✅] Saved {len(anomalies)} anomalies → {out_json}")

