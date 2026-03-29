# JSSP — Simulated Annealing

Simulated Annealing (SA) metaheuristic for the **Job Shop Scheduling Problem
(JSSP)**, following the foundational approach of Van Laarhoven, Aarts &
Lenstra (1992).

## Algorithm overview

### Disjunctive-graph model

A JSSP instance is modelled as a **disjunctive graph** where:

| Element | Meaning |
|---|---|
| **Node** | One operation (job *j*, step *k*) |
| **Conjunctive arc** | Fixed precedence within a job: *(j, k) → (j, k+1)* |
| **Disjunctive arc** | Variable machine ordering: operations sharing a machine are connected by a pair of opposite arcs; exactly one direction is chosen |

A feasible schedule corresponds to an **acyclic orientation** of all
disjunctive arcs. The **makespan** equals the longest path (critical path)
from source to sink.

### N1 neighbourhood (Van Laarhoven et al., 1992)

A neighbour is obtained by **reversing one disjunctive arc on the critical
path** — i.e. swapping two adjacent operations on the same machine that both
lie on the critical path. By Theorem 1 of the reference paper, such a
reversal always yields an acyclic graph (feasible schedule).

The implementation traces a single critical path via a backward pass after
the forward longest-path computation, collecting all disjunctive arcs
encountered. One of these arcs is chosen uniformly at random and reversed.

### Cooling schedule

| Parameter | Description | Default |
|---|---|---|
| **T₀** | Initial temperature, auto-calibrated so ≈ 80 % of worsening moves are accepted | computed |
| **α** | Geometric cooling factor: *T_{k+1} = α · T_k* | 0.95 |
| **Markov-chain length** | Transitions per temperature level ≈ *n + m* | adaptive |
| **Stopping** | Time limit **or** no improvement for 40 consecutive temperature levels | configurable |

### Initial solution

The best schedule among three greedy dispatching rules is used as the
starting point:

- **SPT** — Shortest Processing Time
- **LRPT** — Longest Remaining Processing Time
- **FIFO** — First In, First Out (earliest available job)

## Code structure

```
JSSP-SA/
├── parser.py   — JSON dataset loader (parses the 'matrix' field)
├── sa.py       — SA algorithm + CLI entry point
└── README.md   — this file
```

### `parser.py`

- `load_instances(json_path)` → list of
  `(num_jobs, num_machines, machines, processing, optimal, instance_id)`

### `sa.py`

- `simulated_annealing(...)` — core SA solver, returns the best makespan.
- `compute_makespan_and_critical_swaps(...)` — forward-pass schedule
  evaluation + backward-trace N1 move generation.
- `greedy_solution(...)` — dispatching-rule initial schedule.
- `main()` — loads the dataset, solves all instances, writes `results.csv`.

## Usage

```bash
# Run from the JSSP-SA directory (defaults to Data/starjob_1k.json)
python JSSP_SA/sa.py

# Custom dataset path and time limit (seconds per instance)
python JSSP_SA/sa.py Data/starjob_1k.json 2.0
```

### Output

A CSV file `results.csv` with columns:

| Column | Description |
|---|---|
| `sample_no` | 1-based instance index |
| `instance_id` | Instance path / identifier |
| `raw_result` | Makespan returned by SA |
| `accuracy` | `(optimal / raw_result) × 100`, capped at 100 % |
| `time_required` | Wall-clock time in seconds |

A summary (average / min / max accuracy) is printed to stdout.

## References

1. Van Laarhoven, P.J.M., Aarts, E.H.L., and Lenstra, J.K. (1992).
   **"Job shop scheduling by simulated annealing."**
   *Operations Research*, 40(1), 113–125.
   https://doi.org/10.1287/opre.40.1.113

2. Nowicki, E. and Smutnicki, C. (1996).
   **"A fast taboo search algorithm for the job shop problem."**
   *Management Science*, 42(6), 797–813.
   *(Introduced the block-boundary refinement of the N1 neighbourhood.)*

3. Kirkpatrick, S., Gelatt, C.D., and Vecchi, M.P. (1983).
   **"Optimization by simulated annealing."**
   *Science*, 220(4598), 671–680.
   *(Original SA framework.)*
