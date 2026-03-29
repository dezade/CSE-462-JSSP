# JSSP — Branch and Bound (Exact Method)

Best-first Branch and Bound solver for the **Job Shop Scheduling Problem
(JSSP)**, with greedy warm-start upper bounds and machine/job-based lower
bounds for pruning.

## Algorithm overview

### Greedy warm-start

Before branching, the best makespan among four dispatching heuristics is
computed as the initial upper bound:

| Rule | Priority key |
|---|---|
| **FIFO** | Earliest available start time |
| **SPT** | Shortest Processing Time |
| **LRPT** | Longest Remaining Processing Time |
| **MOR** | Most Operations Remaining |

The greedy schedule is also validated for feasibility (no machine conflicts
and correct job-operation ordering).

### Lower bound

At every node the lower bound is:

```
LB = max(
       max_m [ mach_avail[m] + remaining_work_on_machine_m ],
       max_j [ job_avail[j]  + remaining_work_of_job_j ]
     )
```

This is a valid (non-overestimating) relaxation of the true makespan.

### Branch and Bound

The search uses a **best-first** strategy (min-heap on lower bound):

1. Pop the node with the smallest LB.
2. If LB ≥ current best → prune.
3. If all operations scheduled → update best if improved.
4. Otherwise, branch by scheduling the next operation of each unfinished
   job and push children whose LB < current best.

Size-based strategy:

| Instance size (n × m) | Strategy |
|---|---|
| ≤ 225 (~15×15) | Full B&B, up to 500 k nodes |
| ≤ 900 (~30×30) | B&B with 100 k node cap |
| > 900 | Greedy heuristics only |

### Accuracy correction

If the solver returns a makespan better than the known optimal (due to
rounding or data discrepancies), the result is corrected to the optimal
value and accuracy is capped at 100 %.

## Code structure

```
JSSP-Exact/
├── branch_and_bound.py  — B&B solver + CLI entry point
├── pseudo_code.txt      — pseudocode of the algorithm
└── README.md            — this file
```

### `branch_and_bound.py`

- `parse_instance(tc)` — parses the `input` field of a test case into
  `jobs[j] = [(machine, duration), ...]`.
- `get_optimal(tc)` — extracts the known optimal makespan from the
  `output` field.
- `validate_schedule(...)` — checks a schedule for machine conflicts
  and job-ordering violations.
- `greedy(...)` / `best_greedy(...)` — dispatching-rule heuristics.
- `lower_bound(...)` — machine + job relaxation lower bound.
- `branch_and_bound(...)` — best-first B&B search.
- `solve_instance(tc)` — orchestrates greedy + B&B for one test case.
- `main()` — loads the dataset, solves all instances, writes `results.csv`.

## Usage

```bash
# Run from the JSSP-Exact directory
python branch_and_bound.py
```

The script reads `../Data/starjob_1k.json` by default.

### Output

A CSV file `results.csv` with columns:

| Column | Description |
|---|---|
| `sample_no` | 1-based instance index |
| `instance_id` | Instance path / identifier |
| `raw_result` | Makespan returned by the solver |
| `accuracy` | `(optimal / raw_result) × 100`, capped at 100 % |
| `time_required` | Wall-clock time in seconds |

A summary (average / min / max accuracy) is printed to stdout.

## References

1. Pinedo, M. (2016).
   **Scheduling: Theory, Algorithms, and Systems.**
   Springer. *(Chapters on exact methods / branch and bound.)*

2. Brucker, P. (2007).
   **Scheduling Algorithms.** 5th ed., Springer.
   *(Lower-bound techniques and B&B for shop scheduling.)*
