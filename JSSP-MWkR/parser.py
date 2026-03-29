import json
import re


def parse_matrix(matrix_string, num_jobs):
    lines = matrix_string.strip().split("\n")

    jobs = []
    processing = []

    for j in range(num_jobs):
        tokens = list(map(int, lines[j + 1].split()))

        machines = []
        times = []

        for k in range(0, len(tokens), 2):
            machines.append(tokens[k])
            times.append(tokens[k + 1])

        jobs.append(machines)
        processing.append(times)

    return jobs, processing


def extract_makespan(output_string):
    """
    Extract the optimal makespan from the output field
    """
    match = re.search(r"Makespan:\s*(\d+)", output_string)
    if match:
        return int(match.group(1))
    return None


def load_instances(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    if isinstance(data, list):
        instances = data
    else:
        instances = [data]

    parsed = []

    for inst in instances:
        num_jobs = inst["num_jobs"]
        num_machines = inst["num_machines"]

        machines, times = parse_matrix(inst["matrix"], num_jobs)

        optimal_makespan = extract_makespan(inst["output"])

        parsed.append(
            (num_jobs, num_machines, machines, times, optimal_makespan)
        )

    return parsed