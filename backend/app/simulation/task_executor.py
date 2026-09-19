import math

from dataclasses import dataclass

from ..algorithms.base_algorithm import TaskSpec


@dataclass
class TaskRuntime:
    spec: TaskSpec
    vm_id: str
    status: str = "WAITING"
    assigned_at: float | None = None
    started_at: float | None = None
    expected_finish: float | None = None
    completed_at: float | None = None


def start_task(task, capacity_mips, now):
    if task.status != "ASSIGNED":
        raise ValueError("Only assigned tasks can start.")

    duration = task.spec.work_mi / capacity_mips
    finish = now + duration

    if not math.isfinite(finish) or finish <= now:
        raise ValueError("Task execution exceeds supported timing precision.")

    task.status = "RUNNING"
    task.started_at = now
    task.expected_finish = finish


def complete_task(task):
    if task.status != "RUNNING":
        raise ValueError("Only running tasks can complete.")

    task.completed_at = task.expected_finish
    task.status = "COMPLETED"