# JSSP — Simulated Annealing

Simulated Annealing (SA) metaheuristic for the **Job Shop Scheduling Problem
(JSSP)**, following the foundational approach of Van Laarhoven, Aarts &
Lenstra (1992), with an **improved variant** that adds several enhancements.

## Algorithm variants

The code ships two selectable variants (`--mode`):

| Variant | Key characteristics |
|---|---|
| **Original** | Single critical-path N1 neighbourhood, fixed geometric cooling, early-stop after 40 stagnant levels |
| **Improved** | Block-boundary N5 neighbourhood, reheating + restart, steepest-descent hill-climbing with all-critical-paths N1 |

### Disjunctive-graph model

A JSSP instance is modelled as a **disjunctive graph** where:

| Element | Meaning |
|---|---|
| **Node** | One operation (job *j*, step *k*) |
| **Conjunctive arc** | Fixed precedence within a job: *(j, k) -> (j, k+1)* |
| **Disjunctive arc** | Variable machine ordering: operations sharing a machine are connected by a pair of opposite arcs; exactly one direction is chosen |

A feasible schedule corresponds to an **acyclic orientation** of all
disjunctive arcs. The **makespan** equals the longest path (critical path)
from source to sink.

### N1 neighbourhood

A neighbour is obtained by **reversing one disjunctive arc on the critical
path** — i.e. swapping two adjacent operations on the same machine that both
lie on the critical path. By Theorem 1 of the reference paper, such a
reversal always yields an acyclic graph (feasible schedule).

The original uses the **full N1** neighbourhood (all adjacent-pair swaps on
the single critical path).  The improved variant uses the **N5 block-boundary
refinement** (Nowicki & Smutnicki, 1996): only swaps at the first/last pair
of each critical block are kept.  Interior-block swaps are provably
non-improving, so filtering them means every randomly chosen move has a real
chance of improvement.  The overhead is negligible (one O(L) block scan).
For the final hill-climbing phase the improved variant uses the
**all-critical-paths** evaluator (backward tail computation) to ensure no
improving swap is missed.

### Cooling schedule

| Parameter | Original | Improved |
|---|---|---|
| **T_0** | Auto-calibrated (~80 % acceptance) | Same |
| **alpha** | Fixed geometric: *T_{k+1} = alpha * T_k* | Same |
| **Markov-chain length** | *n + m* (min 100) | Same |
| **Stopping** | Time limit **or** 40 stagnant levels | **Time limit only** (reheating prevents early stop) |

### Reheating & restart (improved only)

When no improvement is found for 30 consecutive temperature levels:

1. Temperature is **reheated** to *0.4 * T_0*.
2. The current solution is **reset to the best known**.
3. A **small random perturbation** (1-2 random swaps) diversifies the restart.

This eliminates premature convergence and fully utilises the time budget.

### Final intensification (improved only)

The last 3 % of the time budget is spent on **steepest-descent hill
climbing** from the best-known solution: all swap candidates (via the
all-critical-paths evaluator) are evaluated and the single best improving
move is applied each step.

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
├── sa.py       — SA algorithm (original + improved) + CLI entry point
└── README.md   — this file
```

### `parser.py`

- `load_instances(json_path)` -> list of
  `(num_jobs, num_machines, machines, processing, optimal, instance_id)`

### `sa.py`

- `simulated_annealing(...)` — original SA solver.
- `simulated_annealing_improved(...)` — improved SA solver (N5 + reheating + hill climbing).
- `compute_makespan_and_critical_swaps(...)` — single-path full-N1 evaluation.
- `compute_makespan_and_block_swaps(...)` — single-path block-boundary N5 evaluation.
- `compute_makespan_and_all_critical_swaps(...)` — all-paths N1 evaluation (hill climbing).
- `greedy_solution(...)` — dispatching-rule initial schedule.
- `main()` — loads the dataset, runs the selected mode, writes CSV(s).

## Usage

Run from the **repository root**:

```bash
# Run the improved variant (default)
python sa.py

# Run the original variant
python sa.py -m original

# Compare both variants side-by-side
python sa.py -m compare

# Full options
python sa.py -i Data/starjob_1k.json -o JSSP-SA/results.csv -t 2.0 -a 0.98 -m compare
```

### CLI arguments

| Flag | Description | Default |
|---|---|---|
| `-i` / `--input` | Path to JSON dataset | `Data/starjob_1k.json` |
| `-o` / `--output` | Output CSV file | `JSSP-SA/results.csv` |
| `-t` / `--time-limit` | Wall-clock seconds per instance | `1.0` |
| `-a` / `--alpha` | Geometric cooling rate | `0.95` |
| `-m` / `--mode` | `original`, `improved`, or `compare` | `improved` |

Run `python sa.py -h` for the built-in help.

### Output

**Single mode** (`original` or `improved`): one CSV file with columns:

| Column | Description |
|---|---|
| `sample_no` | 1-based instance index |
| `instance_id` | Instance path / identifier |
| `raw_result` | Makespan returned by SA |
| `accuracy` | `(optimal / raw_result) * 100`, capped at 100 % |
| `time_required` | Wall-clock time in seconds |

**Compare mode**: two CSV files (`*_original.csv` and `*_improved.csv`) plus
a printed summary showing per-metric deltas and a win/loss/tie breakdown.

## References

1. Van Laarhoven, P.J.M., Aarts, E.H.L., and Lenstra, J.K. (1992).
   **"Job shop scheduling by simulated annealing."**
   *Operations Research*, 40(1), 113-125.
   https://doi.org/10.1287/opre.40.1.113

2. Nowicki, E. and Smutnicki, C. (1996).
   **"A fast taboo search algorithm for the job shop problem."**
   *Management Science*, 42(6), 797-813.
   *(Introduced the block-boundary refinement of the N1 neighbourhood.)*

3. Kirkpatrick, S., Gelatt, C.D., and Vecchi, M.P. (1983).
   **"Optimization by simulated annealing."**
   *Science*, 220(4598), 671-680.
   *(Original SA framework.)*
