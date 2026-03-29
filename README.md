# Job Shop Scheduling Problem — Algorithmic Implementations

A comparative study of three algorithmic approaches to the **Job Shop
Scheduling Problem (JSSP)**: an exact method, a priority dispatching rule,
and a metaheuristic. Developed for CSE 462: Algorithm Engineering Sessional.

## Problem

Given *n* jobs and *m* machines, each job consists of an ordered sequence of
operations with fixed machine assignments and processing times. The goal is
to schedule all operations to **minimise the makespan** (total completion
time) subject to:

1. **Precedence** — operations within a job must execute in order.
2. **Capacity** — each machine processes at most one operation at a time.

JSSP is **strongly NP-Hard** for *m ≥ 3*.

## Implemented Methods

| # | Method | Type | Module |
|---|---|---|---|
| 1 | **Branch & Bound** | Exact | `JSSP-Exact/` |
| 2 | **Most Work Remaining (MWkR)** | Priority Dispatching Rule | `JSSP-MWkR/` |
| 3 | **Simulated Annealing** | Metaheuristic | `JSSP-SA/` |

Each module contains its own `README.md` with algorithm details and pseudocode.

## Repository Structure

```
CSE-462-JSSP/
├── Data/
│   └── starjob_1k.json        # 1,000 benchmark instances
├── JSSP-Exact/
│   ├── branch_and_bound.py     # Branch & Bound solver
│   ├── pseudo_code.txt
│   └── README.md
├── JSSP-MWkR/
│   ├── parser.py               # Dataset parser
│   ├── mwkr.py                 # MWkR dispatcher
│   ├── important.txt
│   └── README.md
├── JSSP-SA/
│   ├── parser.py               # Dataset parser
│   ├── sa.py                   # Simulated Annealing solver
│   └── README.md
├── Plots/                      # Generated comparison plots
├── Presentation/
│   └── main.tex                # Beamer presentation
├── plot.py                     # Comparison visualisation script
├── run.sh                      # Full pipeline script
├── requirements.txt
└── README.md                   # ← you are here
```

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`:

```
matplotlib
numpy
```

Install with:

```bash
pip install -r requirements.txt
```

## Running Each Module Separately

All commands assume the working directory is the **project root**
(`CSE-462-JSSP/`).

### 1. Branch & Bound (Exact)

```bash
cd JSSP-Exact
python branch_and_bound.py
```

Reads `../Data/starjob_1k.json` and writes `results.csv` in the same
directory.

### 2. MWkR (Priority Dispatching)

```bash
cd JSSP-MWkR
python mwkr.py
```

Reads `../Data/starjob_1k.json` and writes `results.csv` in the same
directory.

### 3. Simulated Annealing

```bash
cd JSSP-SA
python sa.py -t 2.0
```

`-t 2.0` sets a 2-second wall-clock budget per instance. Other options:

| Flag | Default | Description |
|---|---|---|
| `-i` | `Data/starjob_1k.json` | Input dataset path |
| `-o` | `JSSP-SA/results.csv` | Output CSV path |
| `-t` | `1.0` | Time limit per instance (seconds) |
| `-a` | `0.95` | Geometric cooling rate |

### 4. Generate Comparison Plots

```bash
python plot.py
```

Clears and regenerates the `Plots/` directory with:

| Output | Description |
|---|---|
| `avg_time_comparison.png` | Bar chart — average runtime per method |
| `avg_accuracy_comparison.png` | Bar chart — average accuracy per method |
| `per_instance_accuracy.png` | Line plot — accuracy across all instances |
| `per_instance_runtime.png` | Line plot — runtime across all instances |
| `accuracy_distribution.png` | Sorted accuracy curves (CDF-style) |
| `summary_table.txt` | Tabulated summary in plain text |

## Running the Full Pipeline

A single shell script runs the entire experiment end-to-end:

```bash
bash run.sh
```

This will:

1. Install Python dependencies from `requirements.txt`
2. Verify that `Data/starjob_1k.json` exists
3. Run Branch & Bound (`JSSP-Exact`)
4. Run Simulated Annealing (`JSSP-SA`)
5. Run MWkR (`JSSP-MWkR`)
6. Generate comparison plots (`plot.py`)

The script stops immediately on any error with a descriptive message.

## Dataset

We use the **Starjob** dataset:

> H. Abgaryan, T. Cazenave, A. Harutyunyan (2025).
> *Starjob: Dataset for LLM-Driven Job Shop Scheduling.*
> arXiv:2503.01877v2.
> https://huggingface.co/datasets/mideavalwisard/Starjob

The full dataset contains 130,000 JSSP instances (from 2×2 up to 50×20)
with known upper bounds computed by OR-Tools. We randomly sampled
**1,000 instances** (`Data/starjob_1k.json`) spanning small, medium, and
large complexity classes.

## References

1. J. Käschel, T. Teich, G. Köbernik, B. Meier (1999).
   *Algorithms for the Job Shop Scheduling Problem — a comparison of
   different methods.* Technische Universität Chemnitz.

2. H. Abgaryan, T. Cazenave, A. Harutyunyan (2025).
   *Starjob: Dataset for LLM-Driven Job Shop Scheduling.*
   arXiv:2503.01877v2.

3. C. Zhang et al. (2020).
   *Learning to dispatch for job shop scheduling via deep reinforcement
   learning.* NeurIPS.

4. M.R. Garey, D.S. Johnson, R. Sethi (1976).
   *The complexity of flowshop and jobshop scheduling.*
   Mathematics of Operations Research.

5. Van Laarhoven, P.J.M., Aarts, E.H.L., and Lenstra, J.K. (1992).
   *Job shop scheduling by simulated annealing.*
   Operations Research, 40(1), 113–125.

6. Pinedo, M. (2016).
   *Scheduling: Theory, Algorithms, and Systems.* Springer.

## Authors

| ID | Name |
|---|---|
| 2005003 | A.H.M Towfique Mahmud |
| 2005004 | Md Zim Mim Siddiqee Sowdha |
| 2005006 | Kowshik Saha Kabya |
| 2005035 | Md Rafiul Islam Nijami |
| 2005055 | Ha Meem |
| 2005111 | Sadnam Faiyaz |
