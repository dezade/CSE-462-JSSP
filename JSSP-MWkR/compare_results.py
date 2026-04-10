import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# -----------------------------
# Resolve directories
# -----------------------------

script_path = Path(__file__).resolve()
parent_dir = script_path.parent
project_dir = parent_dir.parent

plots_dir = project_dir / "Plots"
plots_dir.mkdir(exist_ok=True)

plot_file = plots_dir / "deviation_plot.png"
metrics_file = "metrics.csv"

# -----------------------------
# Load CSV files
# -----------------------------

mwkr_df = pd.read_csv("results.csv")
updated_df = pd.read_csv("results_updated.csv")

instances = mwkr_df["instance_id"]

mwkr = mwkr_df["raw_result"]
mwkr_updated = updated_df["raw_result"]

# -----------------------------
# Get optimal makespan
# -----------------------------

if "optimal_makespan" in mwkr_df.columns:
    optimal = mwkr_df["optimal_makespan"]
elif "optimal_makespan" in updated_df.columns:
    optimal = updated_df["optimal_makespan"]
else:
    raise ValueError("optimal_makespan column not found")

# -----------------------------
# Compute deviation
# -----------------------------

mwkr_dev = ((mwkr - optimal) / optimal) * 100
updated_dev = ((mwkr_updated - optimal) / optimal) * 100

# -----------------------------
# Plot
# -----------------------------

plt.figure(figsize=(12,6))

plt.plot(instances, mwkr_dev, label="MWKR Deviation (%)")
plt.plot(instances, updated_dev, label="MWKR Updated Deviation (%)")

plt.axhline(0, linestyle="--", label="Optimal")

plt.xlabel("Instance ID")
plt.ylabel("Deviation from Optimal (%)")
plt.title("Deviation from Optimal Makespan")

plt.legend()
plt.grid(True)

plt.tight_layout()

# Save plot
plt.savefig(plot_file, dpi=300)

plt.show()

# -----------------------------
# Metrics
# -----------------------------

avg_mwkr = mwkr_dev.mean()
avg_updated = updated_dev.mean()

metrics_df = pd.DataFrame({
    "metric": [
        "average_mwkr_deviation",
        "average_updated_deviation",
        "best_mwkr_deviation",
        "best_updated_deviation",
        "worst_mwkr_deviation",
        "worst_updated_deviation"
    ],
    "value": [
        avg_mwkr,
        avg_updated,
        mwkr_dev.min(),
        updated_dev.min(),
        mwkr_dev.max(),
        updated_dev.max()
    ]
})

metrics_df.to_csv(metrics_file, index=False)

# -----------------------------
# Print summary
# -----------------------------

print("Average MWKR deviation:", avg_mwkr)
print("Average Updated MWKR deviation:", avg_updated)

print(f"\nPlot saved to: {plot_file}")
print(f"Metrics saved to: {metrics_file}")