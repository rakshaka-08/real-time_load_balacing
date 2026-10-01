import math


BACKLOG_STATUSES = frozenset({
    "PENDING",
    "WAITING",
    "ASSIGNED",
})


def _nonnegative_number(value):
    if isinstance(value, bool):
        return 0.0

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0

    if not math.isfinite(number) or number < 0:
        return 0.0

    return number


def _rounded(value):
    return round(float(value), 6)


def calculate_metrics(snapshot):
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be a dictionary.")

    simulated_time = _nonnegative_number(
        snapshot.get("simulated_time", 0.0)
    )

    tasks = snapshot.get("tasks", [])
    vms = snapshot.get("vms", [])

    if not isinstance(tasks, list):
        tasks = []

    if not isinstance(vms, list):
        vms = []

    busy_seconds = [
        _nonnegative_number(vm.get("busy_seconds", 0.0))
        for vm in vms
        if isinstance(vm, dict)
    ]

    total_busy_seconds = math.fsum(busy_seconds)

    available_vm_seconds = (
        simulated_time * len(busy_seconds)
    )

    if available_vm_seconds > 0:
        system_utilization = min(
            100.0,
            (
                total_busy_seconds
                / available_vm_seconds
            )
            * 100.0,
        )
    else:
        system_utilization = 0.0

    if simulated_time > 0:
        vm_utilizations = [
            min(1.0, busy / simulated_time)
            for busy in busy_seconds
        ]
    else:
        vm_utilizations = [
            0.0 for _ in busy_seconds
        ]

    if vm_utilizations:
        mean_load = (
            math.fsum(vm_utilizations)
            / len(vm_utilizations)
        )
    else:
        mean_load = 0.0

    if mean_load > 0:
        variance = math.fsum(
            (load - mean_load) ** 2
            for load in vm_utilizations
        ) / len(vm_utilizations)

        load_imbalance = (
            math.sqrt(variance) / mean_load
        )
    else:
        load_imbalance = 0.0

    response_times = []
    completion_times = []
    backlog_tasks = 0
    backlog_work_mi = 0.0

    for task in tasks:
        if not isinstance(task, dict):
            continue

        status = task.get("status")

        if status == "COMPLETED":
            arrival_time = _nonnegative_number(
                task.get("arrival_time", 0.0)
            )
            completed_at = _nonnegative_number(
                task.get("completed_at", 0.0)
            )

            response_times.append(
                max(0.0, completed_at - arrival_time)
            )
            completion_times.append(completed_at)

        if status in BACKLOG_STATUSES:
            backlog_tasks += 1
            backlog_work_mi += _nonnegative_number(
                task.get("remaining_work_mi", 0.0)
            )

    completed_tasks = len(response_times)
    total_response_time = math.fsum(response_times)

    average_response_time = (
        total_response_time / completed_tasks
        if completed_tasks
        else 0.0
    )

    makespan = max(
        completion_times,
        default=0.0,
    )

    scheduler_execution_seconds = (
        _nonnegative_number(
            snapshot.get(
                "scheduler_execution_seconds",
                snapshot.get(
                    "algorithm_execution_seconds",
                    0.0,
                ),
            )
        )
    )

    redistribution_count = snapshot.get(
        "redistribution_count",
        0,
    )

    if (
        isinstance(redistribution_count, bool)
        or not isinstance(redistribution_count, int)
        or redistribution_count < 0
    ):
        redistribution_count = 0

    return {
        "system_utilization": _rounded(
            system_utilization
        ),
        "total_response_time": _rounded(
            total_response_time
        ),
        "average_response_time": _rounded(
            average_response_time
        ),
        "makespan": _rounded(makespan),
        "load_imbalance": _rounded(
            load_imbalance
        ),
        "backlog_tasks": backlog_tasks,
        "backlog_work_mi": _rounded(
            backlog_work_mi
        ),
        "scheduler_execution_seconds": _rounded(
            scheduler_execution_seconds
        ),
        "redistribution_count": (
            redistribution_count
        ),
    }