# JSSP — Most Work Remaining (MWkR) Dispatching Rule

Priority-dispatching heuristic for the Job Shop Scheduling Problem (JSSP) using the Most Work Remaining (MWkR) rule, following Pinedo (2016), with an enhanced MWkR + SPT tie-breaking variant.

---

# Algorithm overview

## Dispatching rule

At each scheduling step the algorithm selects the job with the maximum total remaining processing time and schedules its next operation at the earliest feasible time (respecting machine availability and job precedence).

A max-priority queue keyed on remaining work ensures efficient selection.

---

# Original MWkR algorithm

## Idea

MWkR prioritizes jobs with the largest remaining processing time to reduce future congestion and balance machine utilization.

## Pseudocode

MWKR_Schedule(n, m, machines, processing)

- Initialize machine_available, job_available, next_operation, remaining_work
- Insert all jobs into priority queue PQ

While PQ not empty:
    - Select job j with maximum remaining_work
    - op = next_operation[j]

    If job has no remaining operations:
        continue

    start = max(machine_available[machine], job_available[j])
    finish = start + duration

    Update machine and job availability
    Advance operation pointer
    Update remaining work

    If job still has operations:
        reinsert into PQ

Return makespan

---

## Complexity

O(n · m · log n)

---

# Improved heuristic — MWkR + SPT

## Motivation

MWkR alone may treat several jobs with similar remaining work equally. This can lead to suboptimal machine usage. We improve it using a secondary rule: Shortest Processing Time (SPT).

---

## Dispatching rule

1. Compute maximum remaining work among all jobs.
2. Select candidate jobs whose remaining work is within a percentage threshold of the maximum.
3. Among candidates, select the job whose next operation has the smallest processing time.

---

## Pseudocode

MWKR_SPT_Schedule(n, m, machines, processing)

- Initialize machine and job availability
- Compute remaining work and next operations

While unscheduled jobs exist:
    max_work = max remaining work

    candidates = jobs where:
        remaining_work ≥ threshold × max_work

    Select job j from candidates with minimum next operation time

    op = next_operation[j]

    start = max(machine_available[machine], job_available[j])
    finish = start + duration

    Update machine and job availability
    Advance operation
    Decrease remaining work

Return makespan

---

## Threshold rule

The threshold is dynamic and defined as a percentage of the maximum remaining work:

threshold = percentage × max_remaining_work

Example:
- threshold = 0.9 → consider jobs with at least 90% of max remaining work

---

# Why this improvement works

- MWkR ensures long jobs are not delayed excessively
- SPT reduces machine waiting and idle time
- Combined heuristic improves scheduling balance and flow efficiency

---

# Code structure

JSSP-MWkR/
├── parser.py
├── mwkr.py
├── important.txt
└── README.md

---

# parser.py

- parse_matrix() → extracts machine and processing matrices
- extract_makespan() → reads optimal makespan from dataset
- load_instances() → loads all scheduling instances

---

# mwkr.py

- run_mwkr() → original MWkR heuristic
- run_mwkr_spt() → improved MWkR + SPT heuristic
- run_dataset() → runs all instances and exports CSV results

---

# Output format

| Column | Description |
|--------|-------------|
| instance_id | Instance index |
| raw_result | Makespan |
| optimal_makespan | Optimal value if available |
| accuracy | optimal / makespan |

---

# Evaluation metric

Deviation (%) = ((makespan - optimal) / optimal) × 100

---

# Usage

python mwkr.py

---

# References

Pinedo, M. (2016). Scheduling: Theory, Algorithms, and Systems. Springer.