# Simulated Annealing for JSSP: Original vs Improved

This document compares the **original** SA implementation (Van Laarhoven et al., 1992) with an **improved** variant that incorporates three targeted enhancements. Both algorithms were evaluated on **1,000 JSSP benchmark instances** with a wall-clock budget of **2 seconds per instance**.

## Results at a Glance

| Metric | Original | Improved | Delta |
|---|---|---|---|
| **Avg accuracy** | 87.28 % | 90.03 % | **+2.75 %** |
| **Min accuracy** | 72.80 % | 75.86 % | +3.06 % |
| **Max accuracy** | 100.0 % | 100.0 % | 0.0 % |

### Per-instance breakdown (1,000 instances)

| Outcome | Count |
|---|---|
| Improved wins | **849** |
| Original wins | 79 |
| Tied | 72 |

The improved variant produces a better makespan on roughly **85 %** of instances.

---

## Shared Foundation

Both variants share the same core structure, which remains unchanged:

- **Disjunctive-graph model** &mdash; operations are nodes; conjunctive arcs enforce job precedence, disjunctive arcs encode machine orderings.
- **Forward-pass longest-path BFS** &mdash; computes the makespan (critical-path length) via topological BFS over the graph.
- **N1 neighbourhood** &mdash; a neighbour is obtained by swapping two adjacent operations on the same machine that both lie on the critical path, reversing one disjunctive arc (Theorem 1 of Van Laarhoven et al. guarantees acyclicity).
- **Greedy initial solution** &mdash; best of SPT, LRPT, and FIFO dispatching rules.
- **Auto-calibrated T_0** &mdash; initial temperature is set so that approximately 80 % of worsening moves are accepted.
- **Geometric cooling** &mdash; T_{k+1} = alpha * T_k  (default alpha = 0.95).
- **Markov-chain length** &mdash; max(n_jobs + n_machines, 100) transitions per temperature level.

---

## Change 1 &mdash; Block-Boundary N5 Neighbourhood across All Critical Paths

### What changed

| | Original | Improved |
|---|---|---|
| **Critical-path coverage** | Single traced critical path | **All** critical paths (via backward tail computation) |
| **Swap candidates** | Every disjunctive arc on that single path | Only the **boundary pairs** of each critical block, across all critical paths |
| **Evaluator function** | `compute_makespan_and_critical_swaps` | `compute_makespan_and_all_critical_block_swaps` |

### How it works

The evaluator combines two techniques:

1. **All-critical-paths identification** &mdash; A backward tail computation (`tail[v]` = longest path from `finish[v]` to the sink) identifies *every* critical disjunctive arc across *all* machines, not just those on a single traced path. An arc (u &rarr; v) is critical iff `finish[u] == start[v]` and both endpoints satisfy `start[v] + duration[v] + tail[v] == makespan`.

2. **Block-boundary filtering** &mdash; For each machine, consecutive critical arcs are grouped into **critical blocks** (maximal runs of adjacent critical positions). Interior swaps within each block are discarded; only boundary swaps are kept.

```
Machine M3 operation order:  [op_a, op_b, op_c, op_d, op_e, op_f, ...]
Critical arcs on M3:                 ✓      ✓      ✓             ✓
                                ├── block 1 ──┤              │block 2│

Block 1:  (a,b), (b,c), (c,d)  →  keep (a,b) and (c,d), discard (b,c)
Block 2:  (e,f)                 →  keep (e,f)
```

### Which swaps are kept?

For each critical block of length $k$ arcs:
- **Single-arc blocks** ($k = 1$): the arc is kept.
- **Multi-arc blocks** ($k \ge 2$): only the **first** and **last** arcs are kept; all interior arcs are discarded.

### Intuition

Nowicki & Smutnicki (1996) proved that **interior-block swaps can never reduce the makespan**. They merely rearrange operations within a block without changing the longest path through it. Only boundary swaps can alter how the critical path enters or exits a block, potentially shortening it.

The combination of all-critical-paths coverage with block-boundary pruning gives the **smallest possible high-quality move set**:

1. **No improving swap is missed** due to arbitrary single-path tracing. Different critical paths may expose different critical arcs, and the all-paths evaluator captures them all.
2. **Every randomly chosen move has a real chance of improvement.** Provably non-improving interior-block swaps are eliminated.
3. **The cost is acceptable.** The backward tail computation adds one reverse pass over the topological order, roughly doubling the per-call cost compared to a single-path trace. However, the higher move quality more than compensates for the reduced iteration count.

### Code reference

The combined evaluator is implemented in `compute_makespan_and_all_critical_block_swaps` (lines 458-576 of `sa.py`). It performs a forward BFS, a backward tail pass, then per-machine block identification and boundary filtering.

---

## Change 2 &mdash; Reheating with Restart (No Early Termination)

### What changed

| | Original | Improved |
|---|---|---|
| **Stagnation response** | **Terminates** after 40 consecutive non-improving temperature levels | **Reheats** to 0.4 * T_0, restarts from best solution with 1-2 random perturbation swaps |
| **Stopping criterion** | Time limit **or** early stop | Time limit **only** |
| **Stagnation threshold** | 40 levels | 30 levels |

### Intuition

The original SA terminates as soon as 40 consecutive temperature levels pass without improving the best-known solution. On many instances this happens well before the 2-second budget expires, **wasting the remaining computation time**.

The improved variant replaces early termination with a **reheat-and-restart** cycle:

1. **Reset the current solution** to the best known so far (we never lose progress).
2. **Reheat the temperature** to 40 % of T_0. This is warm enough to escape the current basin of attraction but cool enough to avoid accepting arbitrarily bad moves.
3. **Apply 1-2 random perturbation swaps** to the restarted solution. This nudges the search into a slightly different region of the neighbourhood, avoiding re-exploring the same local optimum.
4. **Resume normal geometric cooling** from the reheated temperature.

This cycle can repeat many times within the time budget, each time exploring a different neighbourhood region around the best-known solution. The net effect is that the algorithm **fully utilises** the time budget instead of quitting early.

### Code reference

The reheating logic is at lines 818-835 of `sa.py`, inside the main SA loop. The outer `while` loop is controlled solely by `time.perf_counter() - t0 < sa_deadline`.

---

## Change 3 &mdash; Steepest-Descent Hill Climbing (Final Intensification)

### What changed

| | Original | Improved |
|---|---|---|
| **Post-SA phase** | None | **Steepest-descent hill climbing** using the all-critical-paths evaluator |
| **Time allocation** | 100 % to SA | 97 % SA + **3 % hill climbing** |
| **Evaluator for hill climbing** | N/A | `compute_makespan_and_all_critical_swaps` (considers arcs on *every* critical path) |
| **Move selection** | N/A | Evaluates **all** candidates, picks the single **best** improving swap |

### Intuition

After the SA phase completes, the best-known solution may still have easy improving neighbours that SA missed due to its stochastic acceptance criterion. A brief deterministic hill-climbing phase can squeeze out these final gains.

The hill-climbing phase uses two deliberate design choices:

1. **All-critical-paths evaluator** &mdash; Instead of tracing a single critical path, a backward tail computation identifies *every* disjunctive arc on *any* critical path. This gives the richest possible set of swap candidates, ensuring no improving move is overlooked. This evaluator is more expensive per call, but at the hill-climbing stage we only make a handful of calls (bounded by the number of swap candidates per step, typically 5-15), so the cost is negligible.

2. **Steepest descent** &mdash; Rather than accepting the first improving swap found, all candidates are evaluated and the one that reduces the makespan the most is applied. This greedy selection is optimal for local search where every step counts.

### Code reference

The hill-climbing phase is at lines 839-876 of `sa.py`. The all-critical-paths evaluator (`compute_makespan_and_all_critical_swaps`, lines 348-451) uses a forward BFS to compute `start` and `finish` arrays, then a backward pass over the reverse topological order to compute `tail` values. An operation *v* is critical iff `start[v] + duration[v] + tail[v] == makespan`. A disjunctive arc (u -> v) is a swap candidate iff both u and v are critical and `finish[u] == start[v]`.

---

## Summary of All Changes

| Component | Original | Improved | Why it helps |
|---|---|---|---|
| **Neighbourhood** | Full N1 (all swaps on a single traced critical path) | Block-boundary N5 across all critical paths (boundary pairs only) | Covers all critical paths while eliminating provably non-improving interior swaps |
| **Stagnation** | Early termination after 40 levels | Reheat to 0.4 * T_0 + restart from best with perturbation | Fully utilises time budget; explores multiple basins of attraction |
| **Post-SA** | None | Steepest-descent hill climbing (3 % of budget) with all-critical-paths eval | Deterministic cleanup finds easy final improvements that stochastic SA missed |

---

## References

1. Van Laarhoven, P.J.M., Aarts, E.H.L., and Lenstra, J.K. (1992). "Job shop scheduling by simulated annealing." *Operations Research*, 40(1), 113-125.

2. Nowicki, E. and Smutnicki, C. (1996). "A fast taboo search algorithm for the job shop problem." *Management Science*, 42(6), 797-813. *(Block-boundary N5 neighbourhood.)*

3. Kirkpatrick, S., Gelatt, C.D., and Vecchi, M.P. (1983). "Optimization by simulated annealing." *Science*, 220(4598), 671-680.
