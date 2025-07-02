import json
import requests
from datetime import datetime, timedelta

GRAFANA_API_KEY = "API TOKEN"
GRAFANA_GRAPHITE_URL = "https://grafana.ikarem.io/api/datasources/proxy/uid/000000010/render"
HEADERS = { "Authorization": f"Bearer {GRAFANA_API_KEY}" }

def fetch_series(machine, aggregator, ts, window=24):
    t = datetime.fromisoformat(ts)
    from_ts = int((t - timedelta(hours=window / 2)).timestamp())
    until_ts = int((t + timedelta(hours=window / 2)).timestamp())

    parts = aggregator.split(".")
    if len(parts) < 2:
        print(f"[ERROR] Unexpected aggregator format: {aggregator}")
        return []

    agg_name = parts[0]
    metric_name = ".".join(parts[1:])

    graphite_target = f"statsd.{machine}.gauges.aggregator.agg_length_behind_ratio.{agg_name}.{metric_name}"
    print(f"[INFO] Querying: {graphite_target}")

    params = {
        "target": graphite_target,
        "from": from_ts,
        "until": until_ts,
        "format": "json"
    }

    try:
        r = requests.get(GRAFANA_GRAPHITE_URL, headers=HEADERS, params=params)
        r.raise_for_status()
        return r.json()[0]["datapoints"]
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return []

def compute_stats(datapoints):
    values = [v[0] for v in datapoints if v[0] is not None]
    total_points = len(datapoints)
    valid_points = len(values)

    if not values:
        return None, None, 0.0

    max_val = max(values)
    avg_val = sum(values) / valid_points
    valid_pct = valid_points / total_points if total_points > 0 else 0.0

    return max_val, avg_val, round(valid_pct, 3)

def hydrate_anomalies():
    with open("live_anomalies.json", "r") as f:
        anomalies = json.load(f)

    enriched = []
    for a in anomalies:
        print(f"[INFO] Fetching for {a['machine']} / {a['aggregator']} at {a['timestamp']}")
        datapoints = fetch_series(a["machine"], a["aggregator"], a["timestamp"])
        max_val, avg_val, valid_pct = compute_stats(datapoints)

        a["max_value"] = max_val
        a["avg_value"] = avg_val
        a["valid_pct"] = valid_pct
        enriched.append(a)

    with open("hydrated_anomalies.json", "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"[✅] Saved {len(enriched)} enriched anomalies → hydrated_anomalies.json")

if __name__ == "__main__":
    hydrate_anomalies()

