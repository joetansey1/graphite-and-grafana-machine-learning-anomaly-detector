# 1. Clone the repo
git clone https://github.com/joetansey1/graphite-and-grafana-machine-learning-anomaly-detector
cd graphite-and-grafana-machine-learning-anomaly-detector

# 2. Create and activate virtual environment (optional)
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Export your Grafana API key
export GRAFANA_API_KEY="sk_xxx"  # or use a .env file if preferred

# 5. Train the model using 6 months of CSV history
python presence_train_model9.py

# 6. Run live inference against Grafana for presence aggregators
python live_infer18.py

# 7. Enrich flagged anomalies with additional metrics
python hydrated_anomalies6.py

# 8. Visualize the detected anomalies
python plot_it.py

### 📦 Output Format

Each anomaly includes:
- `machine`: which shard triggered the anomaly
- `aggregator`: the affected presence table
- `timestamp`: when it occurred
- `severity`: based on model prediction confidence
- `max_value`, `avg_value`, `valid_pct`: simple metrics for anomaly explainability

ML Model Details

Feature window: 24-point sliding window over 6 months of historical presence data
Training size: ~8 million samples
Model type: IsolationForest 

Presence Aggregator Anomaly Detection
This repository implements a full-stack anomaly detection pipeline for tracking fleet-wide anomalies across production aggregator metrics — specifically focusing on the presence family of aggregators (e.g., ProbeTablesAggregator). It enables real-time detection and visualization of statistical anomalies across shards, backed by historical model training.

Project Purpose
Modern distributed systems generate an immense volume of telemetry across hundreds of aggregators. This project identifies anomalies in backend presence aggregators that may indicate stalled processing, failing jobs, or unhealthy shards.

By modeling historical data and applying statistical deviation checks at inference time, we can proactively highlight aggregators with outlier behavior — and eventually notify engineering teams via Slack or other channels.

Repository Contents
File	Purpose
presence_train_model9.py	Trains an ML model on 6 months of presence aggregator data from multiple shards
live_infer18.py	Runs live anomaly detection on recent Grafana API data using the trained model
hydrated_anomalies6.py	Enriches raw anomalies with metadata (machine name, aggregator, timestamp, etc.)
plot_it.py	Visualizes anomalies with labeled plots by shard and aggregator

Training: How It Works
The anomaly model was trained using 6 CSVs representing 6 months of agg_length_behind_ratio metrics for individual presence aggregators. These CSVs were:

Exported from Grafana dashboards using aliasByNode queries

Covered metrics like:

ProbeTablesAggregator.network_tag_node_tag_cmx_probe_counts_by_ssid_hour_utc

ProbeTablesAggregator.node_tag_cmx_probe_counts_by_ssid_hour_utc

and similar variants

✅ Consolidation Strategy
Initially, models were considered per-aggregator. But after inspecting value distributions, shapes, and temporal variance, it became clear the presence family shared similar statistical properties (e.g., low variance, rare spikes, high sparsity). We merged all CSVs into a unified training set.

This enabled:

Better generalization

A single model to infer across all presence aggregators

Consistent detection across shards

🧮 Anomaly Detection Logic
The pipeline evaluates agg_length_behind_ratio time series for each shard+aggregator.

Under the Hood
Training:

All data points are standardized (z-score)

Statistical properties (mean, stddev, percentiles) are computed

A model is persisted to presence_model.pkl

Inference:

Grafana API fetches the most recent time series

Model evaluates each point:

Values exceeding p95–p99 thresholds or violating fixed absolute cutoffs (e.g., > 0.05) are flagged

Anomalies are enriched and logged

Hydration:

Anomalies are joined with metadata (e.g., aggregator name, timestamp, shard)

Output saved to hydrated_anomalies.json

Plotting:

plot_it.py generates time series visualizations, highlighting anomaly points with labels and coloring

🔧 Tuning Sensitivity
You can adjust anomaly sensitivity by modifying:

Percentile threshold: p95, p99, p99.9 (default is p99)

Static threshold: Set a lower or higher max_value cutoff (e.g., 0.02 → noisy, 0.1 → stricter)

Valid datapoint ratio: Skip time series that are too sparse (e.g., valid_pct < 0.05)

These can be tuned in the live_infer*.py or hydrated_anomalies*.py scripts.

🧩 Future Work
 Slack integration for alerting high-severity anomalies

 Web dashboard for anomaly browsing

 Auto-tagging or clustering related anomaly spikes

 Extend detection to other aggregator families (e.g., client, connectivity)

 Fine-tune detection models per aggregator type

