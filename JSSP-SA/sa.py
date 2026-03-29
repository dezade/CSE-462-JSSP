#!/usr/bin/env python3
"""
Simulated Annealing for the Job Shop Scheduling Problem (JSSP).

Reference:
    Van Laarhoven, P.J.M., Aarts, E.H.L., and Lenstra, J.K. (1992).
    "Job shop scheduling by simulated annealing."
    Operations Research, 40(1), 113-125.

Neighbourhood structure:
    N1 — reversal of a single disjunctive arc on the critical path.
    Only adjacent operations on the same machine that lie on the critical
    path are considered as swap candidates (Theorem 1 in the paper
    guarantees the resulting graph remains acyclic).

Cooling schedule:
    Geometric: T_{k+1} = alpha * T_k

Initial temperature:
    Auto-calibrated so that ~80 % of worsening moves are accepted at T_0.
"""

import random
import math
import time
import csv
import argparse
from collections import deque

from parser import load_instances


# ─────────────────────────────────────────────────────────────
# Instance pre-processing
# ─────────────────────────────────────────────────────────────

def flatten_instance(n_jobs, n_mach, machines_2d, processing_2d):
    """
    Convert 2-D job-operation arrays to flat arrays indexed by
    op_id = job * n_mach + operation_index.
    """
    total = n_jobs * n_mach
    duration = [0] * total
    op_machine = [0] * total
    for j in range(n_jobs):
        base = j * n_mach
        for k in range(n_mach):
            oid = base + k
            duration[oid] = processing_2d[j][k]
            op_machine[oid] = machines_2d[j][k]
    return duration, op_machine


# ─────────────────────────────────────────────────────────────
# Initial solution via greedy dispatching
# ─────────────────────────────────────────────────────────────

def greedy_solution(n_jobs, n_mach, duration, op_machine, rule="spt"):
    """
    Build a feasible semi-active schedule using a dispatching rule.
    Returns machine_order[m] = list of op_ids in processing order.
    """
    total = n_jobs * n_mach
    job_step = [0] * n_jobs
    job_avail = [0] * n_jobs
    mach_avail = [0] * n_mach
    machine_order = [[] for _ in range(n_mach)]
    remaining = [0] * n_jobs
    for j in range(n_jobs):
        base = j * n_mach
        for k in range(n_mach):
            remaining[j] += duration[base + k]

    for _ in range(total):
        best_j = -1
        best_key = None
        for j in range(n_jobs):
            k = job_step[j]
            if k >= n_mach:
                continue
            oid = j * n_mach + k
            m = op_machine[oid]
            t = duration[oid]
            s = max(job_avail[j], mach_avail[m])
            if rule == "spt":
                key = (t, s, j)
            elif rule == "lrpt":
                key = (-remaining[j], s, j)
            else:                        # fifo
                key = (s, j)
            if best_key is None or key < best_key:
                best_key = key
                best_j = j

        j = best_j
        k = job_step[j]
        oid = j * n_mach + k
        m = op_machine[oid]
        t = duration[oid]
        s = max(job_avail[j], mach_avail[m])

        machine_order[m].append(oid)
        remaining[j] -= t
        job_step[j] += 1
        job_avail[j] = s + t
        mach_avail[m] = s + t

    return machine_order


# ─────────────────────────────────────────────────────────────
# Schedule evaluation & critical-path N1 neighbourhood
# ─────────────────────────────────────────────────────────────

def compute_makespan_and_critical_swaps(n_jobs, n_mach, duration,
                                        op_machine, machine_order):
    """
    1. Forward-pass longest-path computation (topological BFS) on the
       disjunctive graph to obtain the makespan.
    2. Backward trace along *one* critical path to collect N1 swap moves.

    A swap move ``(mc, pos)`` means exchanging
    ``machine_order[mc][pos]`` with ``machine_order[mc][pos+1]`` — i.e.
    reversing a disjunctive arc on the critical path.

    Returns ``(makespan, list_of_swap_moves)``.
    """
    total = n_jobs * n_mach
    start  = [0] * total
    finish = [0] * total
    in_deg = [0] * total
    mach_pred = [-1] * total
    mach_succ = [-1] * total
    op_pos    = [0] * total

    # Build machine predecessor / successor / position maps
    for mc in range(n_mach):
        order = machine_order[mc]
        nops = len(order)
        for i in range(nops):
            oid = order[i]
            op_pos[oid] = i
            if i > 0:
                mach_pred[oid] = order[i - 1]
            if i < nops - 1:
                mach_succ[oid] = order[i + 1]

    # In-degrees (each op has at most 2 predecessors: job + machine)
    for oid in range(total):
        d = 0
        if oid % n_mach > 0:       # has a job predecessor
            d += 1
        if mach_pred[oid] >= 0:     # has a machine predecessor
            d += 1
        in_deg[oid] = d

    # ── forward BFS ──
    queue = deque()
    for oid in range(total):
        if in_deg[oid] == 0:
            queue.append(oid)

    makespan = 0
    while queue:
        oid = queue.popleft()
        f = start[oid] + duration[oid]
        finish[oid] = f
        if f > makespan:
            makespan = f

        k = oid % n_mach
        # job successor
        if k + 1 < n_mach:
            s_id = oid + 1
            if f > start[s_id]:
                start[s_id] = f
            in_deg[s_id] -= 1
            if in_deg[s_id] == 0:
                queue.append(s_id)

        # machine successor
        ms = mach_succ[oid]
        if ms >= 0:
            if f > start[ms]:
                start[ms] = f
            in_deg[ms] -= 1
            if in_deg[ms] == 0:
                queue.append(ms)

    # ── backward trace along one critical path ──
    current = -1
    for oid in range(total):
        if finish[oid] == makespan:
            current = oid
            break

    swaps = []
    while current >= 0:
        s = start[current]
        k = current % n_mach
        mp = mach_pred[current]
        jp = (current - 1) if k > 0 else -1

        nxt = -1
        # Prefer the machine predecessor when it is critical — this arc
        # is a disjunctive arc whose reversal defines an N1 neighbour.
        if mp >= 0 and finish[mp] == s:
            swaps.append((op_machine[current], op_pos[mp]))
            nxt = mp
        elif jp >= 0 and finish[jp] == s:
            nxt = jp

        current = nxt

    return makespan, swaps


# ─────────────────────────────────────────────────────────────
# Simulated Annealing
# ─────────────────────────────────────────────────────────────

def simulated_annealing(n_jobs, n_mach, machines_2d, processing_2d,
                        alpha=0.95, time_limit=1.0):
    """
    Simulated Annealing for JSSP with the N1 critical-path neighbourhood
    (Van Laarhoven et al., 1992).

    Parameters
    ----------
    n_jobs, n_mach : int
        Instance dimensions.
    machines_2d, processing_2d : list[list[int]]
        Job-indexed 2-D arrays of machine assignments and durations.
    alpha : float
        Geometric cooling rate  (T_{k+1} = alpha * T_k).
    time_limit : float
        Wall-clock budget in seconds.

    Returns
    -------
    int
        Best makespan found.
    """
    duration, op_machine = flatten_instance(
        n_jobs, n_mach, machines_2d, processing_2d)

    # ── initial solution: best of several greedy heuristics ──
    best_ms = float("inf")
    best_order = None
    for rule in ("spt", "lrpt", "fifo"):
        order = greedy_solution(
            n_jobs, n_mach, duration, op_machine, rule)
        ms, _ = compute_makespan_and_critical_swaps(
            n_jobs, n_mach, duration, op_machine, order)
        if ms < best_ms:
            best_ms = ms
            best_order = [list(o) for o in order]

    current_order = [list(o) for o in best_order]
    current_ms = best_ms

    # ── auto-calibrate T_0 (target ≈ 80 % acceptance of worsening moves) ──
    _, init_swaps = compute_makespan_and_critical_swaps(
        n_jobs, n_mach, duration, op_machine, current_order)

    worsening = []
    n_samples = min(50, max(len(init_swaps) * 3, 10))
    for _ in range(n_samples):
        if not init_swaps:
            break
        mc, pos = random.choice(init_swaps)
        mo = current_order[mc]
        mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]
        nb_ms, _ = compute_makespan_and_critical_swaps(
            n_jobs, n_mach, duration, op_machine, current_order)
        delta = nb_ms - current_ms
        if delta > 0:
            worsening.append(delta)
        mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]       # undo

    if worsening:
        avg_delta = sum(worsening) / len(worsening)
        T = -avg_delta / math.log(0.8)
    else:
        T = max(1.0, current_ms * 0.01)

    # Markov-chain length per temperature level (≈ neighbourhood size)
    markov_len = max(n_jobs + n_mach, 100)

    no_improve = 0
    max_no_improve = 40

    t0 = time.perf_counter()

    current_ms, swaps = compute_makespan_and_critical_swaps(
        n_jobs, n_mach, duration, op_machine, current_order)

    # ── SA main loop ──
    while True:
        if time.perf_counter() - t0 > time_limit:
            break

        improved = False

        for step in range(markov_len):
            if step % 10 == 0 and time.perf_counter() - t0 > time_limit:
                break

            if not swaps:
                current_ms, swaps = compute_makespan_and_critical_swaps(
                    n_jobs, n_mach, duration, op_machine, current_order)
                if not swaps:
                    break

            mc, pos = random.choice(swaps)
            mo = current_order[mc]
            mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]

            new_ms, new_swaps = compute_makespan_and_critical_swaps(
                n_jobs, n_mach, duration, op_machine, current_order)
            delta = new_ms - current_ms

            if delta <= 0 or (
                T > 1e-12
                and random.random() < math.exp(-delta / T)
            ):
                # accept
                current_ms = new_ms
                swaps = new_swaps
                if current_ms < best_ms:
                    best_ms = current_ms
                    best_order = [list(o) for o in current_order]
                    improved = True
            else:
                # reject — undo swap
                mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]

        if not swaps:
            break

        if improved:
            no_improve = 0
        else:
            no_improve += 1
        if no_improve >= max_no_improve:
            break

        T *= alpha

    return best_ms


# ─────────────────────────────────────────────────────────────
# Accuracy & correction logic (mirrors branch_and_bound.py)
# ─────────────────────────────────────────────────────────────

def process_results(optimal, raw_result):
    """Compute accuracy; cap at 100 % if result beats known optimal."""
    if optimal is None or raw_result is None:
        return raw_result, "N/A"
    if raw_result <= 0:
        return raw_result, "ERROR"
    acc = (optimal / raw_result) * 100
    if acc > 100.0 + 1e-6:
        return optimal, 100.0
    return raw_result, round(min(acc, 100.0), 2)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Simulated Annealing for JSSP "
                    "(Van Laarhoven et al., 1992)")
    ap.add_argument(
        "-i", "--input", default="Data/starjob_1k.json",
        help="path to the JSON dataset (default: Data/starjob_1k.json)")
    ap.add_argument(
        "-o", "--output", default="JSSP-SA/results.csv",
        help="output CSV file (default: JSSP-SA/results.csv)")
    ap.add_argument(
        "-t", "--time-limit", type=float, default=1.0,
        help="wall-clock time limit per instance in seconds (default: 1.0)")
    ap.add_argument(
        "-a", "--alpha", type=float, default=0.95,
        help="geometric cooling rate (default: 0.95)")
    args = ap.parse_args()

    json_path  = args.input
    output_csv = args.output
    time_limit = args.time_limit
    alpha      = args.alpha

    print(f"Loading {json_path} ...")
    instances = load_instances(json_path)
    total = len(instances)
    print(f"Loaded {total} instance(s).\n")

    rows = []
    error_rows = []

    for idx, (n_jobs, n_mach, machines, processing,
              optimal, instance_id) in enumerate(instances):

        print(
            f"[{idx+1}/{total}] {instance_id} "
            f"({n_jobs}j\u00d7{n_mach}m) optimal={optimal}",
            end="  ", flush=True,
        )

        try:
            start_time = time.perf_counter()
            raw_result = simulated_annealing(
                n_jobs, n_mach, machines, processing,
                alpha=alpha, time_limit=time_limit,
            )
            elapsed = round(time.perf_counter() - start_time, 4)
        except Exception as e:
            print(f"EXCEPTION: {e}")
            rows.append({
                "sample_no":     idx + 1,
                "instance_id":   instance_id,
                "raw_result":    "EXCEPTION",
                "accuracy":      "N/A",
                "time_required": 0.0,
            })
            error_rows.append((instance_id, str(e)))
            continue

        final_result, accuracy = process_results(optimal, raw_result)

        warn = ""
        if optimal and raw_result < optimal - 1e-6:
            warn = "  *** BEATS OPTIMAL (corrected) ***"

        print(
            f"result={final_result}  accuracy={accuracy}%  "
            f"time={elapsed}s{warn}"
        )

        rows.append({
            "sample_no":     idx + 1,
            "instance_id":   instance_id,
            "raw_result":    final_result,
            "accuracy":      accuracy,
            "time_required": elapsed,
        })

    # ── write CSV ──
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample_no", "instance_id", "raw_result",
                "accuracy", "time_required",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    # ── summary ──
    print(f"\n{'=' * 65}")
    print(f"Results saved to: {output_csv}")

    numeric_acc = [
        r["accuracy"] for r in rows
        if isinstance(r["accuracy"], (float, int))
    ]
    if numeric_acc:
        avg = round(sum(numeric_acc) / len(numeric_acc), 2)
        mn  = round(min(numeric_acc), 2)
        mx  = round(max(numeric_acc), 2)
        print(
            f"Accuracy  avg={avg}%  min={mn}%  max={mx}%  "
            f"(over {len(numeric_acc)} instances)"
        )

    total_time = round(
        sum(r["time_required"] for r in rows
            if isinstance(r["time_required"], float)),
        2,
    )
    print(f"Total wall time: {total_time}s")

    if error_rows:
        print(f"\n*** {len(error_rows)} EXCEPTIONS detected: ***")
        for eid, emsg in error_rows:
            print(f"  {eid}: {emsg}")


if __name__ == "__main__":
    main()
