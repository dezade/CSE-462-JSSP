from parser import load_instances
import heapq
import csv
import time


def compute_remaining_work(processing):
    return [sum(job) for job in processing]


def run_mwr(num_jobs, num_machines, machines, processing):

    machine_available = [0] * num_machines
    job_available = [0] * num_jobs
    job_next_op = [0] * num_jobs

    remaining_work = compute_remaining_work(processing)

    pq = []
    for j in range(num_jobs):
        heapq.heappush(pq, (-remaining_work[j], j))

    while pq:

        _, j = heapq.heappop(pq)

        op = job_next_op[j]
        if op >= len(processing[j]):
            continue

        machine = machines[j][op]
        duration = processing[j][op]

        start = max(machine_available[machine], job_available[j])
        finish = start + duration

        machine_available[machine] = finish
        job_available[j] = finish

        job_next_op[j] += 1
        remaining_work[j] -= duration

        if job_next_op[j] < len(processing[j]):
            heapq.heappush(pq, (-remaining_work[j], j))

    return max(machine_available)


def run_dataset(json_path, output_csv=None):

    instances = load_instances(json_path)

    results = []

    for idx, (num_jobs, num_machines, machines, processing, optimal) in enumerate(instances):

        start_time = time.perf_counter()

        predicted = run_mwr(num_jobs, num_machines, machines, processing)

        end_time = time.perf_counter()

        runtime = end_time - start_time

        accuracy = (optimal / predicted) * 100 if predicted > 0 else 0

        print(
            f"Instance {idx+1}: "
            f"Predicted={predicted}, "
            f"Optimal={optimal}, "
            f"Accuracy={accuracy:.2f}%, "
            f"Runtime={runtime:.4f}s"
        )

        results.append(
            (
                idx + 1,
                predicted,
                # optimal,
                round(accuracy, 2),
                round(runtime, 6),
            )
        )

    if output_csv:
        with open(output_csv, "w", newline="") as f:
            writer = csv.writer(f)

            writer.writerow(
                [
                    "instance_id",
                    "raw_result",
                    # "optimal_makespan",
                    "accuracy",
                    "runtime_seconds",
                ]
            )

            writer.writerows(results)


def main():

    json_path = "../Data/starjob_1k.json"

    run_dataset(json_path, output_csv="results.csv")


if __name__ == "__main__":
    main()