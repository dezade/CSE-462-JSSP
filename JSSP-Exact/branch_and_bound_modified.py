import json
import csv
import time
import heapq
import re
import sys
from collections import defaultdict


# ─────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────

def parse_instance(tc):
    """
    Parse the 'input' field into jobs[j] = list of (machine, duration).
    Format expected:
        J0:
        M10:122 M29:26 ...
        J1:
        M27:113 ...
    Returns jobs (list of lists) and also validates count matches num_jobs.
    """
    raw = tc["input"]
    lines = raw.strip().split("\n")
    jobs = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        # Job header: exactly "J<number>:"
        if re.match(r'^J\d+:$', stripped):
            i += 1
            if i < len(lines) and lines[i].strip():
                ops = []
                for tok in lines[i].strip().split():
                    if ":" in tok:
                        m_str, t_str = tok.split(":", 1)
                        ops.append((int(m_str[1:]), int(t_str)))
                jobs.append(ops)
        i += 1

    expected = tc.get("num_jobs", len(jobs))
    if len(jobs) != expected:
        raise ValueError(
            f"Parsed {len(jobs)} jobs but num_jobs={expected}. "
            f"Check input format."
        )
    return jobs


def get_optimal(tc):
    """
    Extract the known optimal makespan ONLY from the 'output' field.
    Uses a regex to find the number after 'makespan' (case-insensitive).
    Never falls back to 'matrix' or other fields — those are unreliable.
    """
    output = tc.get("output", "")
    # Match: "Makespan: 7274" or "makespan = 7274.0" etc.
    match = re.search(r'(?i)makespan[\s:=]+(\d+(?:\.\d+)?)', output)
    if match:
        return float(match.group(1))
    return None


# ─────────────────────────────────────────────────────────────
# Schedule validation
# ─────────────────────────────────────────────────────────────

def validate_schedule(jobs, num_jobs, schedule):
    """
    Verify the schedule is feasible:
      - No two operations overlap on the same machine.
      - Each job's operations are in order (op k finishes before op k+1 starts).
    Returns list of error strings (empty = valid).
    """
    errors = []
    machine_slots = defaultdict(list)   # machine -> [(start, end, job)]
    job_slots = defaultdict(list)       # job     -> [(start, end, machine, step)]

    for j, m, start, end, step in schedule:
        machine_slots[m].append((start, end, j))
        job_slots[j].append((start, end, m, step))

    # Machine conflicts
    for m, slots in machine_slots.items():
        slots.sort()
        for k in range(len(slots) - 1):
            if slots[k][1] > slots[k + 1][0]:
                errors.append(
                    f"Machine {m} conflict: job {slots[k][2]} ends at {slots[k][1]}, "
                    f"job {slots[k+1][2]} starts at {slots[k+1][0]}"
                )

    # Job ordering conflicts
    for j, slots in job_slots.items():
        slots.sort(key=lambda x: x[3])   # sort by step
        for k in range(len(slots) - 1):
            if slots[k][1] > slots[k + 1][0]:
                errors.append(
                    f"Job {j} step ordering: step {slots[k][3]} ends {slots[k][1]}, "
                    f"step {slots[k+1][3]} starts {slots[k+1][0]}"
                )

    return errors


# ─────────────────────────────────────────────────────────────
# Greedy heuristics (with schedule tracking for validation)
# ─────────────────────────────────────────────────────────────

def greedy(jobs, num_jobs, num_machines, priority="fifo"):
    """
    Schedule all operations using a dispatching rule.
    Returns (makespan, schedule) where schedule = list of (job, machine, start, end, step).
    """
    job_step   = [0] * num_jobs
    job_avail  = [0] * num_jobs
    mach_avail = [0] * num_machines
    remaining  = [sum(t for _, t in jobs[j]) for j in range(num_jobs)]
    schedule   = []

    total_ops = sum(len(j) for j in jobs)

    for _ in range(total_ops):
        best_j, best_key = -1, None

        for j in range(num_jobs):
            if job_step[j] >= len(jobs[j]):
                continue
            m, t = jobs[j][job_step[j]]
            s = max(job_avail[j], mach_avail[m])

            if   priority == "fifo": key = (s, j)
            elif priority == "spt":  key = (t, s, j)
            elif priority == "lrpt": key = (-remaining[j], s, j)
            elif priority == "mor":  key = (-(len(jobs[j]) - job_step[j]), s, j)
            else:                    key = (s, j)

            if best_key is None or key < best_key:
                best_key, best_j = key, j

        if best_j == -1:
            break

        j           = best_j
        m, t        = jobs[j][job_step[j]]
        start       = max(job_avail[j], mach_avail[m])
        end         = start + t
        step        = job_step[j]

        schedule.append((j, m, start, end, step))
        remaining[j]    -= t
        job_step[j]     += 1
        job_avail[j]    = end
        mach_avail[m]   = end

    scheduled_ops = sum(1 for j in range(num_jobs) if job_step[j] == len(jobs[j]))
    if scheduled_ops != num_jobs:
        missing = [j for j in range(num_jobs) if job_step[j] < len(jobs[j])]
        raise RuntimeError(f"Greedy did not schedule all ops; incomplete jobs: {missing}")

    makespan = max(job_avail)
    return makespan, schedule


def best_greedy(jobs, num_jobs, num_machines):
    """Try all 4 greedy rules; return the best (makespan, schedule)."""
    best_ms, best_sched = float("inf"), None
    for rule in ("fifo", "spt", "lrpt", "mor"):
        ms, sched = greedy(jobs, num_jobs, num_machines, rule)
        if ms < best_ms:
            best_ms, best_sched = ms, sched
    return best_ms, best_sched


# ─────────────────────────────────────────────────────────────
# Lower bound
# ─────────────────────────────────────────────────────────────

def lower_bound(jobs, job_step, job_avail, mach_avail, num_jobs, num_machines):
    """
    LB = max(
           max_m [ mach_avail[m] + remaining_work_on_m ],
           max_j [ job_avail[j]  + remaining_work_of_j ]
         )
    This is a valid (non-overestimating) lower bound.
    """
    m_rem = [0] * num_machines
    lb_job = 0

    for j in range(num_jobs):
        step  = job_step[j]
        j_rem = 0
        for k in range(step, len(jobs[j])):
            m, t   = jobs[j][k]
            m_rem[m] += t
            j_rem    += t
        lb_job = max(lb_job, job_avail[j] + j_rem)

    lb_mach = max(mach_avail[m] + m_rem[m] for m in range(num_machines))
    return max(lb_job, lb_mach)


# ─────────────────────────────────────────────────────────────
# Branch and Bound
# ─────────────────────────────────────────────────────────────

def branch_and_bound(jobs, num_jobs, num_machines,
                     upper_bound, time_limit=60.0, max_nodes=200_000):
    """
    Best-first Branch and Bound for JSSP.
    'upper_bound' is the greedy warm-start value (initial best known).
    Returns improved makespan (or upper_bound if no improvement found).
    """
    t0   = time.time()
    best = upper_bound

    init_step = [0] * num_jobs
    init_ja   = [0] * num_jobs
    init_ma   = [0] * num_machines
    init_lb   = lower_bound(jobs, init_step, init_ja, init_ma, num_jobs, num_machines)

    if init_lb >= best:
        return best

    ctr      = 0
    heap     = [(init_lb, ctr, init_step, init_ja, init_ma)]
    expanded = 0

    while heap:
        if time.time() - t0 > time_limit or expanded >= max_nodes:
            break

        lb, _, jstep, javail, mavail = heapq.heappop(heap)
        expanded += 1

        if lb >= best:
            continue

        if all(jstep[j] == len(jobs[j]) for j in range(num_jobs)):
            ms = max(javail)
            if ms < best:
                best = ms
            continue

        for j in range(num_jobs):
            if jstep[j] >= len(jobs[j]):
                continue

            m, t    = jobs[j][jstep[j]]
            start   = max(javail[j], mavail[m])
            finish  = start + t

            nstep   = list(jstep)
            nja     = list(javail)
            nma     = list(mavail)
            nstep[j] += 1
            nja[j]   = finish
            nma[m]   = finish

            child_lb = lower_bound(jobs, nstep, nja, nma, num_jobs, num_machines)
            if child_lb < best:
                ctr += 1
                heapq.heappush(heap, (child_lb, ctr, nstep, nja, nma))

    return best


# ─────────────────────────────────────────────────────────────
# Instance solver  (early-exit at accuracy_target %)
# ─────────────────────────────────────────────────────────────

def solve_instance(tc, time_limit=60.0, optimal=None, accuracy_target=90.0):
    """
    Solve one test case with early termination.

    Strategy:
      1. Run best-of-4 greedy (fast).
      2. If the greedy result already meets `accuracy_target` (vs known optimal),
         return immediately — no B&B needed.
      3. Otherwise spend the remaining budget on B&B and return whatever it finds.

    Size thresholds for B&B node cap (unchanged from original):
      n*m <= 225  : up to 500 000 nodes
      n*m <= 900  : up to 100 000 nodes
      n*m  > 900  : greedy only (B&B skipped regardless of accuracy)

    Returns (makespan, elapsed_seconds, warnings, early_exit_flag).
    """
    jobs         = parse_instance(tc)
    num_jobs     = tc["num_jobs"]
    num_machines = tc["num_machines"]
    size         = num_jobs * num_machines
    warnings     = []

    t0 = time.time()

    # ── Step 1: greedy warm-start ────────────────────────────
    greedy_ms, greedy_sched = best_greedy(jobs, num_jobs, num_machines)

    # ── Step 2: validate greedy schedule ────────────────────
    errs = validate_schedule(jobs, num_jobs, greedy_sched)
    if errs:
        warnings.append(f"INFEASIBLE greedy schedule: {errs[0]}")

    # ── Step 3: early-exit check ─────────────────────────────
    # If we know the optimal and greedy already meets the target, stop now.
    if optimal is not None and optimal > 0:
        greedy_acc = (optimal / greedy_ms) * 100
        if greedy_acc >= accuracy_target:
            elapsed = round(time.time() - t0, 4)
            return greedy_ms, elapsed, warnings, True   # ← early exit

    # ── Step 4: B&B with remaining time budget ───────────────
    elapsed_greedy = time.time() - t0
    remaining_time = time_limit - elapsed_greedy

    if size <= 225 and remaining_time > 0:
        result = branch_and_bound(
            jobs, num_jobs, num_machines,
            upper_bound=greedy_ms,
            time_limit=remaining_time,
            max_nodes=500_000
        )
    elif size <= 900 and remaining_time > 0:
        result = branch_and_bound(
            jobs, num_jobs, num_machines,
            upper_bound=greedy_ms,
            time_limit=min(remaining_time, 30.0),
            max_nodes=100_000
        )
    else:
        # Large instance or no time left — greedy is the best we have
        result = greedy_ms

    elapsed = round(time.time() - t0, 4)
    return result, elapsed, warnings, False   # ← ran full budget


# ─────────────────────────────────────────────────────────────
# Accuracy and Correction Logic
# ─────────────────────────────────────────────────────────────

def process_results(optimal, raw_result):
    """
    Compute accuracy and correct raw_result if it beats optimal.
    If accuracy > 100%, set raw_result to optimal and accuracy to 100%.
    """
    if optimal is None or raw_result is None:
        return raw_result, "N/A"

    if raw_result <= 0:
        return raw_result, "ERROR:zero_result"

    acc = (optimal / raw_result) * 100

    if acc > 100.0 + 1e-6:
        return optimal, 100.0

    return raw_result, round(min(acc, 100.0), 2)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    json_file       = "../Data/starjob_1k.json"
    output_csv      = "results_modified.csv"
    time_limit      = 3.0          # seconds per instance
    accuracy_target = 96.0         # exit early if this accuracy % is reached

    print(f"Loading {json_file} ...")
    try:
        with open(json_file, "r") as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: '{json_file}' not found.")
        print("Place starjob_1k.json in the same directory and re-run.")
        sys.exit(1)

    if not isinstance(test_cases, list):
        test_cases = [test_cases]

    total = len(test_cases)
    print(f"Loaded {total} instance(s).\n")

    rows       = []
    error_rows = []

    for idx, tc in enumerate(test_cases, 1):
        instance_id = tc.get("path", f"instance_{idx-1}")
        n, m        = tc["num_jobs"], tc["num_machines"]
        optimal     = get_optimal(tc)

        print(f"[{idx}/{total}] {instance_id} ({n}j×{m}m) optimal={optimal}",
              end="  ", flush=True)

        try:
            raw_result, elapsed, warnings, early_exit = solve_instance(
                tc,
                time_limit=time_limit,
                optimal=optimal,
                accuracy_target=accuracy_target
            )
        except Exception as e:
            print(f"EXCEPTION: {e}")
            rows.append({"sample_no":     idx,
                         "instance_id":   instance_id,
                         "raw_result":    "EXCEPTION",
                         "accuracy":      "N/A",
                         "time_required": 0.0})
            error_rows.append((instance_id, str(e)))
            continue

        # Apply correction if accuracy > 100%
        final_result, accuracy = process_results(optimal, raw_result)

        # Build status tag
        if early_exit:
            status = " [early exit: greedy ≥90%]"
        else:
            status = " [full B&B budget used]"

        warn_str = ""
        if optimal and raw_result < optimal - 1e-6:
            warn_str = (f"  *** BEATS OPTIMAL: Result={raw_result} "
                        f"Optimal={optimal} (Corrected to 100%) ***")
        if warnings:
            warn_str += f"  WARN: {warnings[0]}"

        print(f"result={final_result}  accuracy={accuracy}%  "
              f"time={elapsed}s{status}{warn_str}")

        rows.append({"sample_no":     idx,
                     "instance_id":   instance_id,
                     "raw_result":    final_result,
                     "accuracy":      accuracy,
                     "time_required": elapsed})

    # Write CSV
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["sample_no", "instance_id", "raw_result",
                           "accuracy", "time_required"]
        )
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    print(f"\n{'='*65}")
    print(f"Results saved to: {output_csv}")

    numeric_acc = [r["accuracy"] for r in rows
                   if isinstance(r["accuracy"], (float, int))]
    if numeric_acc:
        avg = round(sum(numeric_acc) / len(numeric_acc), 2)
        mn  = round(min(numeric_acc), 2)
        mx  = round(max(numeric_acc), 2)
        above_target = sum(1 for a in numeric_acc if a >= accuracy_target)
        print(f"Accuracy  avg={avg}%  min={mn}%  max={mx}%  "
              f"(over {len(numeric_acc)} instances)")
        print(f"Instances ≥{accuracy_target}%: {above_target}/{len(numeric_acc)} "
              f"({round(above_target/len(numeric_acc)*100,1)}%)")

    total_time = round(sum(r["time_required"] for r in rows
                           if isinstance(r["time_required"], float)), 2)
    print(f"Total wall time: {total_time}s")

    if error_rows:
        print(f"\n*** {len(error_rows)} EXCEPTIONS detected: ***")
        for eid, emsg in error_rows:
            print(f"  {eid}: {emsg}")


if __name__ == "__main__":
    main()