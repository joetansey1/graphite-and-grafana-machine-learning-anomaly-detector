import json
import matplotlib.pyplot as plt

# Load hydrated anomalies
with open("hydrated_anomalies.json", "r") as f:
    anomalies = json.load(f)

# Sort by descending max_value
anomalies.sort(key=lambda x: x.get("max_value", 0), reverse=True)

# Prepare plot data
labels = [f'{a["machine"]}\n{a["aggregator"]}' for a in anomalies]
values = [a.get("max_value", 0) for a in anomalies]
severities = [a.get("severity", "low").lower() for a in anomalies]

# Optional: severity-based color map
color_map = {
    "high": "red",
    "medium": "orange",
    "low": "green"
}
colors = [color_map.get(s, "gray") for s in severities]

# Plot
plt.figure(figsize=(14, 6))
plt.bar(labels, values, color=colors)
plt.xticks(rotation=90, fontsize=8)
plt.ylabel("Max Value")
plt.title("Hydrated Anomalies by Shard & Aggregator")
plt.tight_layout()
plt.grid(axis="y", linestyle="--", alpha=0.5)

plt.show()

