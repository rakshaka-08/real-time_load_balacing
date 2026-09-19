import math

from threading import RLock

from ..algorithms.base_algorithm import (
    AlgorithmResult,
    SchedulingProblem,
    validate_number,
)
from .task_executor import TaskRuntime
from .vm_scheduler import VMRuntime
from .load_balancer import rebalance_queues


class SimulationEngine:
    def __init__(self, problem, result, overload_thresholds, enable_redistribution=True,):
        if not isinstance(enable_redistribution, bool):
            raise ValueError("enable_redistribution must be a boolean.")

        self.enable_redistribution = enable_redistribution
        self._redistributions = []
        if not isinstance(problem, SchedulingProblem):
            raise ValueError("problem must be a SchedulingProblem.")

        if not isinstance(result, AlgorithmResult):
            raise ValueError("result must be an AlgorithmResult.")

        if not isinstance(overload_thresholds, dict):
            raise ValueError("overload_thresholds must be a dictionary.")

        vm_ids = {vm.id for vm in problem.vms}

        if set(overload_thresholds) != vm_ids:
            raise ValueError("Supply one overload threshold per VM.")

        thresholds = {
            vm_id: validate_number(value, "overload_threshold")
            for vm_id, value in overload_thresholds.items()
        }

        verified_schedule = problem.evaluate(result.schedule.task_order)

        if verified_schedule != result.schedule:
            raise ValueError(
                "Algorithm result does not match this scheduling problem."
            )

        self.problem = problem
        self.result = result
        self.overload_thresholds = thresholds

        self._lock = RLock()
        self._status = "CREATED"
        self._clock = 0.0
        self._error = None

        assignment_map = {
            assignment.task_id: assignment.vm_id
            for assignment in result.schedule.assignments
        }

        self._tasks = {
            task.id: TaskRuntime(
                spec=task,
                vm_id=assignment_map[task.id],
            )
            for task in problem.tasks
        }

        self._vms = {
            vm.id: VMRuntime(
                spec=vm,
                overload_threshold=thresholds[vm.id],
            )
            for vm in problem.vms
        }

        # This order already respects arrivals and candidate priority.
        self._dispatch_order = tuple(
            assignment.task_id
            for assignment in result.schedule.assignments
        )

    def _process_current_time(self):
        for vm in self._vms.values():
            vm.complete_if_due(self._tasks, self._clock)

        for task_id in self._dispatch_order:
            task = self._tasks[task_id]

            if (
                task.status == "WAITING"
                and task.spec.arrival_time <= self._clock
            ):
                task.status = "ASSIGNED"
                task.assigned_at = self._clock
                self._vms[task.vm_id].queue.append(task_id)

        # Start work on idle VMs before evaluating queued overload.
        for vm in self._vms.values():
            vm.dispatch(self._tasks, self._clock)

        if self.enable_redistribution:
            migrations = rebalance_queues(
                self._vms,
                self._tasks,
                self._clock,
            )
            self._redistributions.extend(migrations)

            # An idle destination can immediately start a transferred task.
            for vm in self._vms.values():
                vm.dispatch(self._tasks, self._clock)

        if all(
            task.status == "COMPLETED"
            for task in self._tasks.values()
        ):
            self._status = "COMPLETED"

    def _next_event_time(self):
        event_times = [
            task.spec.arrival_time
            for task in self._tasks.values()
            if task.status == "WAITING"
        ]

        event_times.extend(
            task.expected_finish
            for task in self._tasks.values()
            if task.status == "RUNNING"
        )

        return min(event_times) if event_times else None

    def _mark_failed(self, error):
        self._status = "FAILED"
        self._error = str(error)

        for task in self._tasks.values():
            if task.status == "RUNNING":
                task.status = "FAILED"

    def start(self):
        with self._lock:
            if self._status != "CREATED":
                raise ValueError("Only a created simulation can start.")

            self._status = "RUNNING"

            try:
                self._process_current_time()
            except Exception as exc:
                self._mark_failed(exc)
                raise

            return self.snapshot()

    def advance(self, seconds):
        seconds = validate_number(
            seconds, "seconds", allow_zero=True
        )

        with self._lock:
            if self._status == "CREATED":
                raise ValueError("Start the simulation before advancing.")

            if self._status != "RUNNING":
                return self.snapshot()

            target = self._clock + seconds

            if not math.isfinite(target):
                raise ValueError("Requested simulation time is too large.")

            try:
                while self._status == "RUNNING":
                    event_time = self._next_event_time()

                    if event_time is None:
                        raise RuntimeError(
                            "Active simulation has no executable events."
                        )

                    if event_time < self._clock:
                        raise RuntimeError(
                            "Simulation event would move time backward."
                        )

                    if event_time > target:
                        self._clock = target
                        break

                    self._clock = event_time
                    self._process_current_time()

                    if self._clock == target:
                        break

            except Exception as exc:
                self._mark_failed(exc)
                raise

            return self.snapshot()

    def pause(self):
        with self._lock:
            if self._status != "RUNNING":
                raise ValueError("Only a running simulation can pause.")

            self._status = "PAUSED"
            return self.snapshot()

    def resume(self):
        with self._lock:
            if self._status != "PAUSED":
                raise ValueError("Only a paused simulation can resume.")

            self._status = "RUNNING"
            return self.snapshot()

    def stop(self):
        with self._lock:
            if self._status not in {"CREATED", "RUNNING", "PAUSED"}:
                raise ValueError(
                    "Only a created, running, or paused simulation can stop."
                )

            self._status = "STOPPED"
            return self.snapshot()

    def reset(self):
        with self._lock:
            if self._status not in {"COMPLETED", "STOPPED", "FAILED"}:
                raise ValueError(
                    "Stop or finish the simulation before resetting."
                )

            return SimulationEngine(
                self.problem,
                self.result,
                dict(self.overload_thresholds),
                enable_redistribution=self.enable_redistribution,
            )
    def snapshot(self):
        with self._lock:
            task_records = []

            for task in self._tasks.values():
                remaining_work = task.spec.work_mi

                if task.status == "COMPLETED":
                    remaining_work = 0.0
                elif task.started_at is not None:
                    capacity = self._vms[task.vm_id].spec.capacity_mips
                    remaining_work = max(
                        0.0,
                        task.spec.work_mi
                        - capacity * (self._clock - task.started_at),
                    )

                task_records.append({
                    "id": task.spec.id,
                    "work_mi": task.spec.work_mi,
                    "arrival_time": task.spec.arrival_time,
                    "vm_id": (
                        None if task.status == "WAITING"
                        else task.vm_id
                    ),
                    "status": task.status,
                    "assigned_at": task.assigned_at,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                    "remaining_work_mi": remaining_work,
                })

            vm_records = [
                {
                    "id": vm.spec.id,
                    "capacity_mips": vm.spec.capacity_mips,
                    "overload_threshold": vm.overload_threshold,
                    "status": vm.status(self._tasks, self._status),
                    "current_task_id": vm.current_task_id,
                    "queued_task_ids": list(vm.queue),
                    "queued_seconds": vm.queued_seconds(self._tasks),
                    "busy_seconds": vm.busy_seconds(
                        self._tasks, self._clock
                    ),
                }
                for vm in self._vms.values()
            ]

            return {
                "status": self._status,
                "simulated_time": self._clock,
                "algorithm": self.result.algorithm,
                "algorithm_execution_seconds": (
                    self.result.execution_seconds
                ),
                "seed": self.result.seed,
                "initial_overload_thresholds": dict(self.overload_thresholds),
                "redistribution_enabled": self.enable_redistribution,
                "redistribution_count": len(self._redistributions),
                "redistributions": [
                    dict(migration)
                    for migration in self._redistributions
                ],
                "error": self._error,
                "tasks": task_records,
                "vms": vm_records,
                "completed_tasks": sum(
                    task.status == "COMPLETED"
                    for task in self._tasks.values()
                ),
                "total_tasks": len(self._tasks),
            }