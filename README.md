# 📊 Graphite & Grafana ML Anomaly Detector

This project uses real-time metrics from a Grafana-Graphite backend to detect anomalies using a trained ML model. It helps identify backend misbehavior (latency spikes, aggregator stalls, etc.) that aren't easily caught by traditional alerting.

---

## 🔧 Scripts Overview

* **`presence_train_model9.py`**:
  Loads and merges 6 months of historical `presence` data from CSVs and trains a consolidated ML anomaly detection model.

* **`live_infer18.py`**:
  Uses the trained model to identify anomalies in real-time from Grafana (via API), focusing on the `presence` aggregator family.

* **`hydrated_anomalies6.py`**:
  Enriches each anomaly by pulling the 24-hour time window around it and calculating useful summary stats: `max_value`, `avg_value`, and `valid_pct` (valid data coverage).

* **`plot_it.py`**:
  Plots all hydrated anomalies with shard ID, aggregator, max value, and timestamp for easy visual inspection and demo.

---

## 🚀 Quickstart

```bash
git clone https://github.com/joetansey1/graphite-and-grafana-machine-learning-anomaly-detector.git
cd graphite-and-grafana-machine-learning-anomaly-detector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python presence_train_model9.py     # Train model from 6 CSVs
python live_infer18.py              # Run detection using Grafana API
python hydrated_anomalies6.py       # Pull context data for anomalies
python plot_it.py                   # Generate demo plot with annotations
```

---

## 🧠 How the Anomaly Detection Works

We pulled 6 months of data for each sub-aggregator in the `presence` family into individual CSVs.
Each CSV had the same shape: a timestamp and an `agg_length_behind_ratio` value.

Upon inspection, we noticed that all aggregators had similar statistical behavior (distribution shape, periodicity), so we merged them into one unified dataset to train a single model.

We use a stats-driven detection model that:

* Computes rolling windows and lag metrics
* Learns normal `agg_length_behind_ratio` ranges
* Flags anomalies that deviate sharply at `24h` or `72h` lags
* Produces anomaly records like:

```json
{
  "machine": "n211-primary-meraki-com",
  "aggregator": "ProbeTablesAggregator.node_tag_cmx_probe_counts_by_ssid_hour_utc",
  "timestamp": "2025-07-01T21:14:05.749118",
  "severity": "high",
  "max_value": 0.099,
  "avg_value": 0.096,
  "valid_pct": 0.029
}
```

---

## 📈 Screenshot
https://github.com/joetansey1/graphite-and-grafana-machine-learning-anomaly-detector/blob/main/anomaly_n294-primary-meraki-com_ProbeTablesAggregator_network_tag_node_tag_cmx_probe_hll_hour.png

---

## 🛠️ Future Extensions

* Slack integration for pushing anomaly alerts to ops channels
* Per-shard anomaly summary & trend reports
* Fleet-wide meta-anomaly detection
* Switch between strict (p99) vs. permissive (p95) detection thresholds
* Fine-tune duration and shape-based heuristics

---

## 📄 License

MIT (add `LICENSE` file if needed)
