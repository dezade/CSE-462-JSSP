#!/usr/bin/env python3
"""
Comparative visualisation of JSSP solver results.

Reads results CSVs from the three methods (Exact, Simulated Annealing, MWkR)
and produces:
    1. Bar chart  — average time per method
    2. Bar chart  — average accuracy per method
    3. Text table — tabulated summary (same data as the bar charts)
    4. Per-instance accuracy curves   (all ~1 k instances)
    5. Per-instance runtime curves    (all ~1 k instances)

All outputs are saved to ./Plots/ (cleared on every run).
"""

import os
import shutil
import csv
import statistics
import textwrap

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

METHODS = {
    "Exact (Original)": {
        "csv": "JSSP-Exact/results.csv",
        "acc_col": "accuracy",
        "time_col": "time_required(sec)",
        "color": "#6366f1",       # indigo-500
    },
    "Exact (Modified)": {
        "csv": "JSSP-Exact/results_modified.csv",
        "acc_col": "accuracy",
        "time_col": "time_required",
        "color": "#818cf8",       # indigo-400
    },
    "SA (Original)": {
        "csv": "JSSP-SA/results_original.csv",
        "acc_col": "accuracy",
        "time_col": "time_required",
        "color": "#f59e0b",       # amber-500
    },
    "SA (Improved)": {
        "csv": "JSSP-SA/results_improved.csv",
        "acc_col": "accuracy",
        "time_col": "time_required",
        "color": "#fbbf24",       # amber-400
    },
    "MWkR (Original)": {
        "csv": "JSSP-MWkR/results.csv",
        "acc_col": "accuracy",
        "time_col": "runtime_seconds",
        "color": "#10b981",       # emerald-500
    },
    "MWkR (Updated)": {
        "csv": "JSSP-MWkR/results_updated.csv",
        "acc_col": "accuracy",
        "time_col": "runtime_seconds",
        "color": "#34d399",       # emerald-400
    },
}

PLOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Plots")

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _safe_float(val):
    """Convert a CSV cell to float; return None if not numeric."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def load_method(cfg):
    """Return (accuracies, times) as lists of float."""
    accs, times = [], []
    with open(cfg["csv"], newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            a = _safe_float(row[cfg["acc_col"]])
            t = _safe_float(row[cfg["time_col"]])
            if a is not None:
                accs.append(a)
            if t is not None:
                times.append(t)
    return accs, times


def _apply_style(ax, title, ylabel, xlabel=None):
    """Apply a consistent look to a matplotlib Axes."""
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel(ylabel, fontsize=11)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=10)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=8))


# ──────────────────────────────────────────────────────────────
# Plot 1  –  Average Time (bar chart)
# ──────────────────────────────────────────────────────────────

def plot_avg_time(data):
    """Bar chart comparing average runtime across methods."""
    names   = list(data.keys())
    means   = [statistics.mean(data[n]["times"]) for n in names]
    colors  = [METHODS[n]["color"] for n in names]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(names, means, color=colors, width=0.5, edgecolor="white",
                  linewidth=1.2, zorder=3)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.4f} s", ha="center", va="bottom", fontsize=10,
                fontweight="semibold")

    _apply_style(ax, "Average Runtime per Instance", "Time (seconds)")
    ax.tick_params(axis='x', rotation=90)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "avg_time_comparison.png"), dpi=200)
    plt.close(fig)
    print("  * avg_time_comparison.png")


# ──────────────────────────────────────────────────────────────
# Plot 2  –  Average Accuracy (bar chart)
# ──────────────────────────────────────────────────────────────

def plot_avg_accuracy(data):
    """Bar chart comparing average accuracy across methods."""
    names   = list(data.keys())
    means   = [statistics.mean(data[n]["accs"]) for n in names]
    colors  = [METHODS[n]["color"] for n in names]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(names, means, color=colors, width=0.5, edgecolor="white",
                  linewidth=1.2, zorder=3)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.2f}%", ha="center", va="bottom", fontsize=10,
                fontweight="semibold")

    _apply_style(ax, "Average Accuracy per Instance", "Accuracy (%)")
    ax.set_ylim(0, 105)
    ax.tick_params(axis='x', rotation=90)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "avg_accuracy_comparison.png"), dpi=200)
    plt.close(fig)
    print("  * avg_accuracy_comparison.png")


# ──────────────────────────────────────────────────────────────
# Plot 3  –  Text summary table
# ──────────────────────────────────────────────────────────────

def write_summary_table(data):
    """Write a formatted text table to Plots/summary_table.txt."""
    header = (
        f"{'Method':<24} | {'Avg Acc (%)':>12} | {'Min Acc (%)':>12} | "
        f"{'Max Acc (%)':>12} | {'Avg Time (s)':>13} | "
        f"{'Min Time (s)':>13} | {'Max Time (s)':>13} | {'Instances':>10}"
    )
    sep = "-" * len(header)

    lines = [
        sep,
        header,
        sep,
    ]

    for name, vals in data.items():
        accs  = vals["accs"]
        times = vals["times"]
        lines.append(
            f"{name:<24} | {statistics.mean(accs):>12.2f} | "
            f"{min(accs):>12.2f} | {max(accs):>12.2f} | "
            f"{statistics.mean(times):>13.6f} | {min(times):>13.6f} | "
            f"{max(times):>13.6f} | {len(accs):>10}"
        )

    lines.append(sep)

    table_text = "\n".join(lines) + "\n"

    path = os.path.join(PLOT_DIR, "summary_table.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(table_text)
    print("  " + "summary_table.txt")
    print()
    print(table_text)


# ──────────────────────────────────────────────────────────────
# Plot 4  –  Per-instance accuracy curves
# ──────────────────────────────────────────────────────────────

def plot_instance_accuracy(data):
    """
    Line plot showing accuracy for every instance (sorted by instance
    index) so the three methods can be compared side-by-side.
    """
    fig, ax = plt.subplots(figsize=(14, 5))

    for name, vals in data.items():
        accs = vals["accs"]
        x = np.arange(1, len(accs) + 1)
        ax.plot(x, accs, linewidth=0.6, alpha=0.75,
                color=METHODS[name]["color"], label=name)

    ax.legend(fontsize=10, framealpha=0.9)
    _apply_style(ax, "Per-Instance Accuracy Comparison",
                 "Accuracy (%)", "Instance Index")
    ax.set_ylim(0, 110)
    ax.grid(axis="both", linestyle="--", alpha=0.3, zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "per_instance_accuracy.png"), dpi=200)
    plt.close(fig)
    print("  * per_instance_accuracy.png")


# ──────────────────────────────────────────────────────────────
# Plot 5  –  Per-instance runtime curves
# ──────────────────────────────────────────────────────────────

def plot_instance_time(data):
    """
    Line plot showing runtime for every instance so the three methods
    can be compared side-by-side.
    """
    fig, ax = plt.subplots(figsize=(14, 5))

    for name, vals in data.items():
        times = vals["times"]
        x = np.arange(1, len(times) + 1)
        ax.plot(x, times, linewidth=0.6, alpha=0.75,
                color=METHODS[name]["color"], label=name)

    ax.legend(fontsize=10, framealpha=0.9)
    _apply_style(ax, "Per-Instance Runtime Comparison",
                 "Time (seconds)", "Instance Index")
    ax.grid(axis="both", linestyle="--", alpha=0.3, zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "per_instance_runtime.png"), dpi=200)
    plt.close(fig)
    print("  * per_instance_runtime.png")


# ──────────────────────────────────────────────────────────────
# Plot 6  –  Sorted (CDF-style) accuracy curves
# ──────────────────────────────────────────────────────────────

def plot_sorted_accuracy(data):
    """
    Each method's accuracy values are sorted ascending, allowing a
    cumulative-distribution comparison (how many instances reach at
    least X % accuracy).
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    for name, vals in data.items():
        sorted_accs = sorted(vals["accs"])
        y = np.linspace(0, 100, len(sorted_accs))
        ax.plot(sorted_accs, y, linewidth=1.4,
                color=METHODS[name]["color"], label=name)

    ax.legend(fontsize=10, framealpha=0.9)
    _apply_style(ax, "Accuracy Distribution (Sorted)",
                 "Cumulative % of Instances", "Accuracy (%)")
    ax.grid(axis="both", linestyle="--", alpha=0.3, zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "accuracy_distribution.png"), dpi=200)
    plt.close(fig)
    print("  * accuracy_distribution.png")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    # Clear and recreate output directory
    if os.path.exists(PLOT_DIR):
        shutil.rmtree(PLOT_DIR)
    os.makedirs(PLOT_DIR)

    print(f"Output directory: {PLOT_DIR}\n")

    # Load data
    data = {}
    for name, cfg in METHODS.items():
        accs, times = load_method(cfg)
        data[name] = {"accs": accs, "times": times}
        print(f"  Loaded {name}: {len(accs)} instances")

    print()

    # Generate plots & table
    plot_avg_time(data)
    plot_avg_accuracy(data)
    plot_instance_accuracy(data)
    plot_instance_time(data)
    plot_sorted_accuracy(data)
    write_summary_table(data)

    print("Done — all plots saved to ./Plots/")


if __name__ == "__main__":
    main()
