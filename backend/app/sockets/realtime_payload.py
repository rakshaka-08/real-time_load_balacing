from copy import deepcopy


METRIC_FIELDS = (
    "system_utilization",
    "total_response_time",
    "average_response_time",
    "makespan",
    "load_imbalance",
    "backlog_tasks",
    "backlog_work_mi",
    "scheduler_execution_seconds",
    "redistribution_count",
)


def build_realtime_payload(state):
    if not isinstance(state, dict):
        raise ValueError(
            "simulation state must be a dictionary."
        )

    payload = deepcopy(state)
    metrics = payload.get("metrics")

    # Older saved simulations may not contain
    # Module 27 metrics. Their existing payload
    # remains unchanged and still works.
    if not isinstance(metrics, dict):
        return payload

    realtime_metrics = {
        "simulation_id": payload.get("id"),
        "revision": payload.get("revision"),
        "status": payload.get("status"),
        "simulated_time": payload.get(
            "simulated_time",
            0.0,
        ),
        "pending_tasks": payload.get(
            "pending_tasks",
            0,
        ),
        "running_tasks": payload.get(
            "running_tasks",
            0,
        ),
        "completed_tasks": payload.get(
            "completed_tasks",
            0,
        ),
        "total_tasks": payload.get(
            "total_tasks",
            0,
        ),
    }

    for field in METRIC_FIELDS:
        if field in metrics:
            realtime_metrics[field] = metrics[field]

    payload["realtime_metrics"] = (
        realtime_metrics
    )

    return payload