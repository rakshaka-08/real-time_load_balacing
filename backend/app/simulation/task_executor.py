import math

from dataclasses import dataclass

from ..algorithms.base_algorithm import TaskSpec


TASK_STATUSES = {
    "PENDING",
    "WAITING",
    "ASSIGNED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
}


@dataclass
class TaskRuntime:
    spec: TaskSpec
    vm_id: str | None
    status: str = "WAITING"
    assigned_at: float | None = None
    started_at: float | None = None
    expected_finish: float | None = None
    completed_at: float | None = None

    def __post_init__(self):
        if not isinstance(self.spec, TaskSpec):
            raise ValueError("spec must be a TaskSpec.")

        if self.vm_id is not None and not isinstance(self.vm_id, str):
            raise ValueError("vm_id must be a string or None.")

        if self.status not in TASK_STATUSES:
            raise ValueError("Unknown task status.")

        if self.status == "PENDING" and self.vm_id is not None:
            raise ValueError(
                "A pending task cannot already have a VM assignment."
            )


def start_task(task, capacity_mips, now):
    if task.status != "ASSIGNED":
        raise ValueError("Only assigned tasks can start.")

    if task.vm_id is None:
        raise ValueError(
            "An assigned task must have a virtual machine."
        )

    duration = task.spec.work_mi / capacity_mips
    finish = now + duration

    if not math.isfinite(finish) or finish <= now:
        raise ValueError(
            "Task execution exceeds supported timing precision."
        )

    task.status = "RUNNING"
    task.started_at = now
    task.expected_finish = finish


def complete_task(task):
    if task.status != "RUNNING":
        raise ValueError("Only running tasks can complete.")

    task.completed_at = task.expected_finish
    task.status = "COMPLETED"