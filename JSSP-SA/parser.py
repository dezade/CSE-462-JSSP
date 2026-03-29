import json
import re


def parse_matrix(matrix_string, num_jobs):
    """
    Parse the 'matrix' field into machine assignments and processing times.

    Format:
        <num_jobs> <num_machines>
        <machine_1> <time_1> <machine_2> <time_2> ...
        ...

    Returns (machines, processing) where:
        machines[j][k]   = machine ID for job j, operation k
        processing[j][k] = duration for job j, operation k
    """
    lines = matrix_string.strip().split("\n")
    machines = []
    processing = []
    for j in range(num_jobs):
        tokens = list(map(int, lines[j + 1].split()))
        job_machines = []
        job_times = []
        for k in range(0, len(tokens), 2):
            job_machines.append(tokens[k])
            job_times.append(tokens[k + 1])
        machines.append(job_machines)
        processing.append(job_times)
    return machines, processing


def extract_makespan(output_string):
    """Extract the optimal makespan from the 'output' field."""
    match = re.search(r"Makespan:\s*(\d+)", output_string)
    if match:
        return int(match.group(1))
    return None


def load_instances(json_path):
    """Load all JSSP instances from a JSON file."""
    with open(json_path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        instances = data
    else:
        instances = [data]

    parsed = []
    for idx, inst in enumerate(instances):
        num_jobs = inst["num_jobs"]
        num_machines = inst["num_machines"]
        machines, times = parse_matrix(inst["matrix"], num_jobs)
        optimal = extract_makespan(inst["output"])
        instance_id = inst.get("path", f"instance_{idx}")
        parsed.append(
            (num_jobs, num_machines, machines, times, optimal, instance_id)
        )
    return parsed
