from collections import deque
from dataclasses import dataclass, field
from math import fsum

from ..algorithms.base_algorithm import VMSpec
from .task_executor import complete_task, start_task


@dataclass
class VMRuntime:
    spec: VMSpec
    overload_threshold: float
    queue: deque = field(default_factory=deque)
    current_task_id: str | None = None
    completed_busy_seconds: float = 0.0

    def queued_seconds(self, tasks):
        return fsum(
            tasks[task_id].spec.work_mi / self.spec.capacity_mips
            for task_id in self.queue
        )

    def busy_seconds(self, tasks, now):
        ongoing = 0.0

        if self.current_task_id is not None:
            task = tasks[self.current_task_id]
            ongoing = max(0.0, now - task.started_at)

        return self.completed_busy_seconds + ongoing

    def complete_if_due(self, tasks, now):
        if self.current_task_id is None:
            return

        task = tasks[self.current_task_id]

        if task.expected_finish <= now:
            complete_task(task)
            self.completed_busy_seconds += (
                task.completed_at - task.started_at
            )
            self.current_task_id = None

    def dispatch(self, tasks, now):
        if self.current_task_id is not None or not self.queue:
            return

        task_id = self.queue[0]
        task = tasks[task_id]

        start_task(task, self.spec.capacity_mips, now)

        self.queue.popleft()
        self.current_task_id = task_id

    def status(self, tasks, simulation_status):
        if simulation_status == "COMPLETED":
            return "COMPLETED"

        if self.queued_seconds(tasks) > self.overload_threshold:
            return "OVERLOADED"

        if self.current_task_id is not None:
            return "RUNNING"

        return "IDLE"