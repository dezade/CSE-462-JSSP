# JSSP — Most Work Remaining (MWkR) Dispatching Rule

Priority-dispatching heuristic for the **Job Shop Scheduling Problem
(JSSP)** using the **Most Work Remaining (MWkR)** rule, following
Pinedo (2016).

## Algorithm overview

### Dispatching rule

At each scheduling step the algorithm selects the job with the **maximum
total remaining processing time** and schedules its next operation at the
earliest feasible time (respecting both machine availability and job
precedence).

A max-priority queue keyed on remaining work ensures efficient selection.

### Pseudocode

```
MWKR_Schedule(n, m, machines, processing)

  for each machine k:  machine_available[k] ← 0
  for each job j:
      job_available[j]   ← 0
      next_operation[j]  ← 0
      remaining_work[j]  ← Σ processing times of job j

  Insert every job into a max-priority queue PQ

  while PQ is not empty:
      j  ← job with maximum remaining_work
      op ← next_operation[j]

      if job j has no remaining operations: continue

      start  ← max(machine_available[machine], job_available[j])
      finish ← start + duration

      update machine_available, job_available
      advance next_operation[j], reduce remaining_work[j]

      if job j still has operations: re-insert into PQ

  return max(machine_available)         ← makespan
```

### Why MWkR?

MWkR is a well-known constructive heuristic that produces reasonably
good schedules in **O(n · m · log n)** time (with a heap). It tends to
balance machine utilisation by prioritising jobs that still have the most
work ahead, reducing idle gaps on bottleneck machines.

## Code structure

```
JSSP-MWkR/
├── parser.py       — JSON dataset loader (parses the 'matrix' field)
├── mwkr.py         — MWkR dispatcher + CLI entry point
├── important.txt   — algorithm notes & pseudocode
└── README.md       — this file
```

### `parser.py`

- `parse_matrix(matrix_string, num_jobs)` → `(machines, processing)` —
  2-D lists of machine assignments and durations.
- `extract_makespan(output_string)` → `int | None` — pulls the optimal
  makespan from the `output` field.
- `load_instances(json_path)` → list of
  `(num_jobs, num_machines, machines, processing, optimal_makespan)`.

### `mwkr.py`

- `compute_remaining_work(processing)` — sums processing times per job.
- `run_mwr(num_jobs, num_machines, machines, processing)` — core MWkR
  dispatcher, returns the makespan.
- `run_dataset(json_path, output_csv)` — iterates over all instances,
  prints per-instance results, optionally writes CSV.
- `main()` — loads the dataset and writes `results.csv`.

## Usage

```bash
# Run from the JSSP-MWkR directory
python mwkr.py
```

The script reads `../Data/starjob_1k.json` by default.

### Output

A CSV file `results.csv` with columns:

| Column | Description |
|---|---|
| `instance_id` | 1-based instance index |
| `raw_result` | Makespan returned by MWkR |
| `accuracy` | `(optimal / raw_result) × 100` |
| `runtime_seconds` | Wall-clock time in seconds |

Per-instance results are also printed to stdout.

## References

1. Pinedo, M. (2016).
   **Scheduling: Theory, Algorithms, and Systems.**
   Springer. *(Priority dispatching rules for shop scheduling.)*
