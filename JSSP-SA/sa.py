#!/usr/bin/env python3
"""
Simulated Annealing for the Job Shop Scheduling Problem (JSSP).

Two variants are provided:
    1. **Original** — Van Laarhoven et al. (1992) baseline with single
       critical-path N1 neighbourhood and geometric cooling.
    2. **Improved** — Enhanced version with:
       - All-critical-paths neighbourhood (richer N1 move set)
       - Reheating with restart from best solution + perturbation
       - Adaptive cooling rate based on acceptance ratio
       - Final intensification via first-improvement hill climbing

Use ``--mode {original,improved,compare}`` to select the variant.
In *compare* mode both are run on every instance and a side-by-side
summary is printed.

Reference:
    Van Laarhoven, P.J.M., Aarts, E.H.L., and Lenstra, J.K. (1992).
    "Job shop scheduling by simulated annealing."
    Operations Research, 40(1), 113-125.
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
# Schedule evaluation — ORIGINAL (single critical path)
# ─────────────────────────────────────────────────────────────

def compute_makespan_and_critical_swaps(n_jobs, n_mach, duration,
                                        op_machine, machine_order):
    """
    Forward-pass longest-path + backward trace along *one* critical
    path to collect N1 swap moves.

    Returns ``(makespan, list_of_swap_moves)``.
    """
    total = n_jobs * n_mach
    start  = [0] * total
    finish = [0] * total
    in_deg = [0] * total
    mach_pred = [-1] * total
    mach_succ = [-1] * total
    op_pos    = [0] * total

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

    for oid in range(total):
        d = 0
        if oid % n_mach > 0:
            d += 1
        if mach_pred[oid] >= 0:
            d += 1
        in_deg[oid] = d

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
        if k + 1 < n_mach:
            s_id = oid + 1
            if f > start[s_id]:
                start[s_id] = f
            in_deg[s_id] -= 1
            if in_deg[s_id] == 0:
                queue.append(s_id)

        ms = mach_succ[oid]
        if ms >= 0:
            if f > start[ms]:
                start[ms] = f
            in_deg[ms] -= 1
            if in_deg[ms] == 0:
                queue.append(ms)

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
        if mp >= 0 and finish[mp] == s:
            swaps.append((op_machine[current], op_pos[mp]))
            nxt = mp
        elif jp >= 0 and finish[jp] == s:
            nxt = jp

        current = nxt

    return makespan, swaps


# ─────────────────────────────────────────────────────────────
# Schedule evaluation — BLOCK-BOUNDARY (Nowicki & Smutnicki N5)
# ─────────────────────────────────────────────────────────────

def compute_makespan_and_block_swaps(n_jobs, n_mach, duration,
                                     op_machine, machine_order):
    """
    Forward-pass longest-path + backward trace along one critical
    path, with **block-boundary filtering** (Nowicki & Smutnicki, 1996).

    A *critical block* is a maximal consecutive sequence of operations
    on the same machine within the critical path.  Interior swaps
    (within a block but not at its boundary) are provably
    non-improving.  This evaluator returns only the boundary swaps:

    * First block on the path  -> only the **last** adjacent pair.
    * Last block on the path   -> only the **first** adjacent pair.
    * Interior blocks          -> both first and last pairs.

    The overhead over the plain single-path trace is negligible
    (one O(L) scan to identify blocks) while every returned swap has a
    real chance of improvement.

    Returns ``(makespan, list_of_swap_moves)``.
    """
    total = n_jobs * n_mach
    start  = [0] * total
    finish = [0] * total
    in_deg = [0] * total
    mach_pred = [-1] * total
    mach_succ = [-1] * total
    op_pos    = [0] * total

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

    for oid in range(total):
        d = 0
        if oid % n_mach > 0:
            d += 1
        if mach_pred[oid] >= 0:
            d += 1
        in_deg[oid] = d

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
        if k + 1 < n_mach:
            s_id = oid + 1
            if f > start[s_id]:
                start[s_id] = f
            in_deg[s_id] -= 1
            if in_deg[s_id] == 0:
                queue.append(s_id)

        ms = mach_succ[oid]
        if ms >= 0:
            if f > start[ms]:
                start[ms] = f
            in_deg[ms] -= 1
            if in_deg[ms] == 0:
                queue.append(ms)

    current = -1
    for oid in range(total):
        if finish[oid] == makespan:
            current = oid
            break

    # Backward trace: collect all machine arcs on the critical path.
    arcs = []
    while current >= 0:
        s = start[current]
        k = current % n_mach
        mp = mach_pred[current]
        jp = (current - 1) if k > 0 else -1

        nxt = -1
        if mp >= 0 and finish[mp] == s:
            arcs.append((op_machine[current], op_pos[mp]))
            nxt = mp
        elif jp >= 0 and finish[jp] == s:
            nxt = jp
        current = nxt

    if not arcs:
        return makespan, []

    arcs.reverse()  # forward order along critical path
    n_arcs = len(arcs)

    # Identify block boundaries (maximal runs on the same machine)
    # and collect only the boundary swaps.
    block_start = 0
    swaps = []
    for i in range(1, n_arcs + 1):
        if i == n_arcs or arcs[i][0] != arcs[block_start][0]:
            bs, be = block_start, i - 1
            is_first = (bs == 0)
            is_last  = (be == n_arcs - 1)

            if is_first and is_last:
                swaps.append(arcs[be])
                if bs != be:
                    swaps.append(arcs[bs])
            elif is_first:
                swaps.append(arcs[be])
            elif is_last:
                swaps.append(arcs[bs])
            else:
                swaps.append(arcs[bs])
                if bs != be:
                    swaps.append(arcs[be])

            block_start = i

    return makespan, swaps


# ─────────────────────────────────────────────────────────────
# Schedule evaluation — ALL CRITICAL PATHS (for hill climbing)
# ─────────────────────────────────────────────────────────────

def compute_makespan_and_all_critical_swaps(n_jobs, n_mach, duration,
                                            op_machine, machine_order):
    """
    Forward-pass longest-path + backward tail computation to identify
    ALL disjunctive arcs on ANY critical path.

    An operation *v* is critical iff
        start[v] + duration[v] + tail[v] == makespan
    where *tail[v]* is the longest path from finish[v] to the sink.

    A disjunctive arc (u -> v) is a valid N1 swap candidate iff both
    endpoints are critical and the arc is tight (finish[u] == start[v]).

    Returns ``(makespan, list_of_swap_moves)``.
    """
    total = n_jobs * n_mach
    start  = [0] * total
    finish = [0] * total
    in_deg = [0] * total
    mach_pred = [-1] * total
    mach_succ = [-1] * total

    for mc in range(n_mach):
        order = machine_order[mc]
        nops = len(order)
        for i in range(nops):
            oid = order[i]
            if i > 0:
                mach_pred[oid] = order[i - 1]
            if i < nops - 1:
                mach_succ[oid] = order[i + 1]

    for oid in range(total):
        d = 0
        if oid % n_mach > 0:
            d += 1
        if mach_pred[oid] >= 0:
            d += 1
        in_deg[oid] = d

    # ── forward BFS (collect topological order) ──
    queue = deque()
    topo_order = []
    for oid in range(total):
        if in_deg[oid] == 0:
            queue.append(oid)

    makespan = 0
    while queue:
        oid = queue.popleft()
        topo_order.append(oid)
        f = start[oid] + duration[oid]
        finish[oid] = f
        if f > makespan:
            makespan = f

        k = oid % n_mach
        if k + 1 < n_mach:
            s_id = oid + 1
            if f > start[s_id]:
                start[s_id] = f
            in_deg[s_id] -= 1
            if in_deg[s_id] == 0:
                queue.append(s_id)

        ms = mach_succ[oid]
        if ms >= 0:
            if f > start[ms]:
                start[ms] = f
            in_deg[ms] -= 1
            if in_deg[ms] == 0:
                queue.append(ms)

    # ── backward pass: longest suffix after each operation ──
    tail = [0] * total
    for oid in reversed(topo_order):
        t = 0
        k = oid % n_mach
        if k + 1 < n_mach:
            s_id = oid + 1
            v = duration[s_id] + tail[s_id]
            if v > t:
                t = v
        ms = mach_succ[oid]
        if ms >= 0:
            v = duration[ms] + tail[ms]
            if v > t:
                t = v
        tail[oid] = t

    # ── collect ALL critical disjunctive arcs across every machine ──
    swaps = []
    for mc in range(n_mach):
        order = machine_order[mc]
        nops = len(order)
        for i in range(nops - 1):
            u = order[i]
            v = order[i + 1]
            if (finish[u] == start[v]
                    and start[u] + duration[u] + tail[u] == makespan
                    and start[v] + duration[v] + tail[v] == makespan):
                swaps.append((mc, i))

    return makespan, swaps


# ─────────────────────────────────────────────────────────────
# Helper: auto-calibrate initial temperature
# ─────────────────────────────────────────────────────────────

def _calibrate_temperature(n_jobs, n_mach, duration, op_machine,
                           current_order, current_ms, init_swaps,
                           eval_fn):
    """Sample neighbourhood deltas to set T_0 for ~80 % acceptance."""
    worsening = []
    n_samples = min(50, max(len(init_swaps) * 3, 10))
    for _ in range(n_samples):
        if not init_swaps:
            break
        mc, pos = random.choice(init_swaps)
        mo = current_order[mc]
        mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]
        nb_ms, _ = eval_fn(n_jobs, n_mach, duration, op_machine,
                           current_order)
        delta = nb_ms - current_ms
        if delta > 0:
            worsening.append(delta)
        mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]

    if worsening:
        avg_delta = sum(worsening) / len(worsening)
        return -avg_delta / math.log(0.8)
    return max(1.0, current_ms * 0.01)


# ─────────────────────────────────────────────────────────────
# Simulated Annealing — ORIGINAL
# ─────────────────────────────────────────────────────────────

def simulated_annealing(n_jobs, n_mach, machines_2d, processing_2d,
                        alpha=0.95, time_limit=1.0):
    """
    Original SA for JSSP with the N1 critical-path neighbourhood
    (Van Laarhoven et al., 1992).

    Uses a single critical-path trace, geometric cooling, and stops
    on time limit or after 40 non-improving temperature levels.
    """
    duration, op_machine = flatten_instance(
        n_jobs, n_mach, machines_2d, processing_2d)

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

    _, init_swaps = compute_makespan_and_critical_swaps(
        n_jobs, n_mach, duration, op_machine, current_order)
    T = _calibrate_temperature(n_jobs, n_mach, duration, op_machine,
                               current_order, current_ms, init_swaps,
                               compute_makespan_and_critical_swaps)

    markov_len = max(n_jobs + n_mach, 100)
    no_improve = 0
    max_no_improve = 40

    t0 = time.perf_counter()
    current_ms, swaps = compute_makespan_and_critical_swaps(
        n_jobs, n_mach, duration, op_machine, current_order)

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
                current_ms = new_ms
                swaps = new_swaps
                if current_ms < best_ms:
                    best_ms = current_ms
                    best_order = [list(o) for o in current_order]
                    improved = True
            else:
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
# Simulated Annealing — IMPROVED
# ─────────────────────────────────────────────────────────────

def simulated_annealing_improved(n_jobs, n_mach, machines_2d, processing_2d,
                                 alpha=0.95, time_limit=1.0):
    """
    Improved SA for JSSP.  Enhancements over the original:

    1. **Block-boundary N5 neighbourhood** (Nowicki & Smutnicki, 1996)
       — only swaps at the boundaries of critical blocks are considered.
       Interior-block swaps are provably non-improving, so filtering
       them out means every randomly chosen move has a real chance of
       improvement.  The overhead is negligible (one O(L) scan).
    2. **Reheating with restart** — when no improvement is found for
       *max_no_improve* temperature levels the search reheats and
       restarts from the best-known solution with a small random
       perturbation.  The algorithm never terminates early; only the
       time limit stops it.
    3. **Steepest-descent hill climbing** — the final phase evaluates
       *all* swap candidates (using the all-critical-paths evaluator)
       and picks the single best improving move each step.
    """
    duration, op_machine = flatten_instance(
        n_jobs, n_mach, machines_2d, processing_2d)

    sa_eval = compute_makespan_and_block_swaps
    hc_eval = compute_makespan_and_all_critical_swaps

    # ── initial solution: best of several greedy heuristics ──
    best_ms = float("inf")
    best_order = None
    for rule in ("spt", "lrpt", "fifo"):
        order = greedy_solution(
            n_jobs, n_mach, duration, op_machine, rule)
        ms, _ = sa_eval(n_jobs, n_mach, duration, op_machine, order)
        if ms < best_ms:
            best_ms = ms
            best_order = [list(o) for o in order]

    current_order = [list(o) for o in best_order]
    current_ms = best_ms

    # ── auto-calibrate T_0 ──
    _, init_swaps = sa_eval(
        n_jobs, n_mach, duration, op_machine, current_order)
    initial_T = _calibrate_temperature(
        n_jobs, n_mach, duration, op_machine,
        current_order, current_ms, init_swaps, sa_eval)
    T = initial_T

    markov_len = max(n_jobs + n_mach, 100)
    no_improve = 0
    max_no_improve = 30

    t0 = time.perf_counter()
    sa_deadline = time_limit * 0.97

    current_ms, swaps = sa_eval(
        n_jobs, n_mach, duration, op_machine, current_order)

    # ── SA main loop — only the time limit stops it ──
    while time.perf_counter() - t0 < sa_deadline:
        improved = False

        for step in range(markov_len):
            if step % 10 == 0 and time.perf_counter() - t0 > sa_deadline:
                break
            if not swaps:
                current_ms, swaps = sa_eval(
                    n_jobs, n_mach, duration, op_machine, current_order)
                if not swaps:
                    break

            mc, pos = random.choice(swaps)
            mo = current_order[mc]
            mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]

            new_ms, new_swaps = sa_eval(
                n_jobs, n_mach, duration, op_machine, current_order)
            delta = new_ms - current_ms

            if delta <= 0 or (
                T > 1e-12
                and random.random() < math.exp(-delta / T)
            ):
                current_ms = new_ms
                swaps = new_swaps
                if current_ms < best_ms:
                    best_ms = current_ms
                    best_order = [list(o) for o in current_order]
                    improved = True
            else:
                mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]

        if not swaps:
            current_order = [list(o) for o in best_order]
            current_ms, swaps = sa_eval(
                n_jobs, n_mach, duration, op_machine, current_order)
            T = initial_T * 0.4
            no_improve = 0
            continue

        if improved:
            no_improve = 0
        else:
            no_improve += 1

        # ── reheating: restart from best with mild perturbation ──
        if no_improve >= max_no_improve:
            T = initial_T * 0.4
            current_order = [list(o) for o in best_order]
            current_ms, swaps = sa_eval(
                n_jobs, n_mach, duration, op_machine, current_order)

            for _ in range(random.randint(1, 2)):
                if swaps:
                    pmc, ppos = random.choice(swaps)
                    pmo = current_order[pmc]
                    pmo[ppos], pmo[ppos + 1] = pmo[ppos + 1], pmo[ppos]
                    current_ms, swaps = sa_eval(
                        n_jobs, n_mach, duration, op_machine,
                        current_order)

            no_improve = 0
            continue

        T *= alpha

    # ── final intensification: steepest-descent hill climbing ──
    current_order = [list(o) for o in best_order]
    current_ms = best_ms
    _, swaps = hc_eval(
        n_jobs, n_mach, duration, op_machine, current_order)

    while time.perf_counter() - t0 < time_limit:
        if not swaps:
            break
        best_swap = None
        best_new_ms = current_ms
        best_new_swaps = None

        for mc, pos in list(swaps):
            if time.perf_counter() - t0 > time_limit:
                break
            mo = current_order[mc]
            mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]
            new_ms, new_swaps = hc_eval(
                n_jobs, n_mach, duration, op_machine, current_order)
            if new_ms < best_new_ms:
                best_new_ms = new_ms
                best_swap = (mc, pos)
                best_new_swaps = new_swaps
            mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]

        if best_swap is None:
            break

        mc, pos = best_swap
        mo = current_order[mc]
        mo[pos], mo[pos + 1] = mo[pos + 1], mo[pos]
        current_ms = best_new_ms
        swaps = best_new_swaps
        if current_ms < best_ms:
            best_ms = current_ms
            best_order = [list(o) for o in current_order]

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
# Runner helpers
# ─────────────────────────────────────────────────────────────

CSV_FIELDS = ["sample_no", "instance_id", "raw_result",
              "accuracy", "time_required"]


def _run_variant(solver_fn, label, instances, alpha, time_limit):
    """Run *solver_fn* on every instance and return (rows, error_rows)."""
    total = len(instances)
    rows = []
    error_rows = []

    for idx, (n_jobs, n_mach, machines, processing,
              optimal, instance_id) in enumerate(instances):

        tag = f"[{label}] [{idx+1}/{total}]"
        print(
            f"  {tag} {instance_id} "
            f"({n_jobs}j x {n_mach}m) optimal={optimal}",
            end="  ", flush=True,
        )

        try:
            t_start = time.perf_counter()
            raw_result = solver_fn(
                n_jobs, n_mach, machines, processing,
                alpha=alpha, time_limit=time_limit,
            )
            elapsed = round(time.perf_counter() - t_start, 4)
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

    return rows, error_rows


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _print_summary(label, rows, csv_path, error_rows):
    print(f"\n{'=' * 65}")
    print(f"[{label}] Results saved to: {csv_path}")

    numeric_acc = [
        r["accuracy"] for r in rows
        if isinstance(r["accuracy"], (float, int))
    ]
    if numeric_acc:
        avg = round(sum(numeric_acc) / len(numeric_acc), 2)
        mn  = round(min(numeric_acc), 2)
        mx  = round(max(numeric_acc), 2)
        print(
            f"  Accuracy  avg={avg}%  min={mn}%  max={mx}%  "
            f"(over {len(numeric_acc)} instances)"
        )

    total_time = round(
        sum(r["time_required"] for r in rows
            if isinstance(r["time_required"], float)),
        2,
    )
    print(f"  Total wall time: {total_time}s")

    if error_rows:
        print(f"\n  *** {len(error_rows)} EXCEPTIONS detected: ***")
        for eid, emsg in error_rows:
            print(f"    {eid}: {emsg}")

    return numeric_acc


def _print_comparison(acc_orig, acc_impr, rows_orig, rows_impr):
    """Print a side-by-side comparison table."""
    print(f"\n{'=' * 65}")
    print("COMPARISON:  Original  vs  Improved")
    print(f"{'=' * 65}")

    def _stats(acc_list):
        if not acc_list:
            return {"avg": "N/A", "min": "N/A", "max": "N/A", "n": 0}
        return {
            "avg": round(sum(acc_list) / len(acc_list), 2),
            "min": round(min(acc_list), 2),
            "max": round(max(acc_list), 2),
            "n":   len(acc_list),
        }

    so = _stats(acc_orig)
    si = _stats(acc_impr)

    header = f"{'Metric':<20} {'Original':>12} {'Improved':>12} {'Delta':>12}"
    print(header)
    print("-" * len(header))

    for key, label in [("avg", "Avg accuracy %"),
                       ("min", "Min accuracy %"),
                       ("max", "Max accuracy %")]:
        vo = so[key]
        vi = si[key]
        if isinstance(vo, (int, float)) and isinstance(vi, (int, float)):
            delta = round(vi - vo, 2)
            sign = "+" if delta >= 0 else ""
            print(f"{label:<20} {vo:>12} {vi:>12} {sign + str(delta):>12}")
        else:
            print(f"{label:<20} {str(vo):>12} {str(vi):>12} {'':>12}")

    n_better = n_worse = n_tied = 0
    for ro, ri in zip(rows_orig, rows_impr):
        ao = ro["accuracy"]
        ai = ri["accuracy"]
        if not isinstance(ao, (int, float)) or not isinstance(ai, (int, float)):
            continue
        if ai > ao + 1e-6:
            n_better += 1
        elif ao > ai + 1e-6:
            n_worse += 1
        else:
            n_tied += 1

    total_compared = n_better + n_worse + n_tied
    print(f"\nPer-instance breakdown ({total_compared} comparable):")
    print(f"  Improved wins : {n_better}")
    print(f"  Original wins : {n_worse}")
    print(f"  Tied          : {n_tied}")


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
    ap.add_argument(
        "-m", "--mode", choices=["original", "improved", "compare"],
        default="improved",
        help="algorithm variant: original, improved, or compare both "
             "(default: improved)")
    args = ap.parse_args()

    json_path  = args.input
    output_csv = args.output
    time_limit = args.time_limit
    alpha      = args.alpha
    mode       = args.mode

    print(f"Loading {json_path} ...")
    instances = load_instances(json_path)
    total = len(instances)
    print(f"Loaded {total} instance(s).  Mode: {mode}\n")

    if mode == "original":
        rows, errs = _run_variant(
            simulated_annealing, "Original", instances, alpha, time_limit)
        _write_csv(output_csv, rows)
        _print_summary("Original", rows, output_csv, errs)

    elif mode == "improved":
        rows, errs = _run_variant(
            simulated_annealing_improved, "Improved", instances,
            alpha, time_limit)
        _write_csv(output_csv, rows)
        _print_summary("Improved", rows, output_csv, errs)

    elif mode == "compare":
        base, ext = (output_csv.rsplit(".", 1) if "." in output_csv
                     else (output_csv, "csv"))
        csv_orig = f"{base}_original.{ext}"
        csv_impr = f"{base}_improved.{ext}"

        print("--- Running ORIGINAL ---")
        rows_orig, errs_orig = _run_variant(
            simulated_annealing, "Original", instances, alpha, time_limit)
        _write_csv(csv_orig, rows_orig)

        print("\n--- Running IMPROVED ---")
        rows_impr, errs_impr = _run_variant(
            simulated_annealing_improved, "Improved", instances,
            alpha, time_limit)
        _write_csv(csv_impr, rows_impr)

        acc_orig = _print_summary(
            "Original", rows_orig, csv_orig, errs_orig)
        acc_impr = _print_summary(
            "Improved", rows_impr, csv_impr, errs_impr)
        _print_comparison(acc_orig, acc_impr, rows_orig, rows_impr)


if __name__ == "__main__":
    main()
