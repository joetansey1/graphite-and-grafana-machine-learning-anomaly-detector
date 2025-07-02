import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Constants
GRAFANA_API_KEY = "API TOKEN"
GRAFANA_GRAPHITE_URL = "GRAPHITE URL"
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

HEADERS = {
    "Authorization": f"Bearer {GRAFANA_API_KEY}"
}

# Load model (retrained version)
model = joblib.load("presence_model2.pkl")

# Time bounds
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
            print(f"[WARN] Failed for {machine} {aggregator} — {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Timeout or connection error for {machine} / {aggregator}: {e}")
    return None

def detect_anomaly_for_series(series_data, machine, aggregator):
    if not series_data:
        return None
    for series in series_data:
        datapoints = [v[0] for v in series["datapoints"] if v[0] is not None]
        if len(datapoints) < model.n_features_in_:
            continue
        X = pd.DataFrame(
            [datapoints[-model.n_features_in_:]],
            columns=[f"t-{i}" for i in range(model.n_features_in_)]
        )
        y_pred = model.predict(X)[0]
        if y_pred == -1:  # -1 = anomaly for IsolationForest
            ts = datetime.utcnow().isoformat()
            return {
                "machine": machine,
                "aggregator": aggregator,
                "timestamp": ts,
                "severity": "high"
            }
    return None

# Detect anomalies
anomalies = []
for machine in MACHINES:
    for aggregator in AGGREGATORS:
        print(f"[INFO] Querying {machine} / {aggregator}...")
        series_data = query_series(machine, aggregator)
        result = detect_anomaly_for_series(series_data, machine, aggregator)
        if result:
            print(f"[ANOMALY] {result}")
            anomalies.append(result)

# Save results
with open("live_anomalies.json", "w") as f:
    json.dump(anomalies, f, indent=2)

