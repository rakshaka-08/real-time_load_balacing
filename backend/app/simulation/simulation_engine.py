import math

from collections import deque
from threading import RLock

from ..algorithms.base_algorithm import (
    AlgorithmResult,
    SchedulingProblem,
    TaskSpec,
    validate_number,
)
from .load_balancer import rebalance_queues
from .task_executor import TaskRuntime
from .vm_scheduler import VMRuntime


class SimulationEngine:
    def __init__(
        self,
        problem,
        result,
        overload_thresholds,
        enable_redistribution=True,
    ):
        if not isinstance(enable_redistribution, bool):
            raise ValueError(
                "enable_redistribution must be a boolean."
            )

        if not isinstance(problem, SchedulingProblem):
            raise ValueError(
                "problem must be a SchedulingProblem."
            )

        if not isinstance(result, AlgorithmResult):
            raise ValueError(
                "result must be an AlgorithmResult."
            )

        if not isinstance(overload_thresholds, dict):
            raise ValueError(
                "overload_thresholds must be a dictionary."
            )

        vm_ids = {
            vm.id
            for vm in problem.vms
        }

        if set(overload_thresholds) != vm_ids:
            raise ValueError(
                "Supply one overload threshold per VM."
            )

        thresholds = {
            vm_id: validate_number(
                value,
                "overload_threshold",
            )
            for vm_id, value
            in overload_thresholds.items()
        }

        verified_schedule = problem.evaluate(
            result.schedule.task_order
        )

        if verified_schedule != result.schedule:
            raise ValueError(
                "Algorithm result does not match this "
                "scheduling problem."
            )

        self.problem = problem
        self.result = result
        self.overload_thresholds = thresholds
        self.enable_redistribution = enable_redistribution

        self._lock = RLock()
        self._status = "CREATED"
        self._clock = 0.0
        self._error = None
        self._redistributions = []
        self._pending_task_ids = deque()
        self._workload_open = False

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

        self._dispatch_order = [
            assignment.task_id
            for assignment in result.schedule.assignments
        ]

    def _process_current_time(self):
        for vm in self._vms.values():
            vm.complete_if_due(
                self._tasks,
                self._clock,
            )

        for task_id in self._dispatch_order:
            task = self._tasks[task_id]

            if (
                task.status == "WAITING"
                and task.spec.arrival_time <= self._clock
            ):
                if task.vm_id is None:
                    raise RuntimeError(
                        "A scheduled task has no VM assignment."
                    )

                task.status = "ASSIGNED"
                task.assigned_at = self._clock

                self._vms[
                    task.vm_id
                ].queue.append(task_id)

        for vm in self._vms.values():
            vm.dispatch(
                self._tasks,
                self._clock,
            )

        if self.enable_redistribution:
            migrations = rebalance_queues(
                self._vms,
                self._tasks,
                self._clock,
            )

            self._redistributions.extend(
                migrations
            )

            for vm in self._vms.values():
                vm.dispatch(
                    self._tasks,
                    self._clock,
                )

        if (
            not self._workload_open
            and all(
                task.status == "COMPLETED"
                for task in self._tasks.values()
            )
        ):
            self._status = "COMPLETED"

    def _next_event_time(self):
        event_times = [
            task.spec.arrival_time
            for task in self._tasks.values()
            if (
                task.status == "WAITING"
                and task.spec.arrival_time > self._clock
            )
        ]

        event_times.extend(
            task.expected_finish
            for task in self._tasks.values()
            if task.status == "RUNNING"
        )

        return (
            min(event_times)
            if event_times
            else None
        )

    def _mark_failed(self, error):
        self._status = "FAILED"
        self._error = str(error)

        for task in self._tasks.values():
            if task.status == "RUNNING":
                task.status = "FAILED"

    def add_tasks(self, tasks):
        try:
            new_tasks = tuple(tasks)
        except TypeError:
            raise ValueError(
                "tasks must be an iterable of "
                "TaskSpec objects."
            ) from None

        if not new_tasks:
            raise ValueError(
                "Supply at least one task."
            )

        if not all(
            isinstance(task, TaskSpec)
            for task in new_tasks
        ):
            raise ValueError(
                "All injected tasks must be "
                "TaskSpec objects."
            )

        incoming_ids = [
            task.id
            for task in new_tasks
        ]

        if len(set(incoming_ids)) != len(incoming_ids):
            raise ValueError(
                "Injected task IDs must be unique."
            )

        with self._lock:
            if self._status not in {
                "CREATED",
                "RUNNING",
                "PAUSED",
            }:
                raise ValueError(
                    "Tasks can only be added to a "
                    "created, running, or paused simulation."
                )

            duplicate_ids = set(
                incoming_ids
            ).intersection(self._tasks)

            if duplicate_ids:
                raise ValueError(
                    "A task with this ID already exists."
                )

            for task in new_tasks:
                self._tasks[task.id] = TaskRuntime(
                    spec=task,
                    vm_id=None,
                    status="PENDING",
                )

                self._pending_task_ids.append(
                    task.id
                )

            return self.snapshot()

    def pending_task_specs(self, limit=None):
        if limit is not None and (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit <= 0
        ):
            raise ValueError(
                "limit must be a positive "
                "integer or None."
            )

        with self._lock:
            task_ids = list(
                self._pending_task_ids
            )

            if limit is not None:
                task_ids = task_ids[:limit]

            return tuple(
                self._tasks[task_id].spec
                for task_id in task_ids
            )

    def vm_specs(self):
        with self._lock:
            return tuple(
                vm.spec
                for vm in self._vms.values()
            )

    def set_workload_open(self, value):
        if not isinstance(value, bool):
            raise ValueError(
                "workload state must be a boolean."
            )

        with self._lock:
            if self._status in {
                "STOPPED",
                "FAILED",
            }:
                raise ValueError(
                    "The workload state cannot change "
                    "after the simulation has stopped "
                    "or failed."
                )

            if (
                self._status == "COMPLETED"
                and value
            ):
                raise ValueError(
                    "A completed simulation cannot "
                    "reopen its workload."
                )

            self._workload_open = value

            if (
                self._status == "RUNNING"
                and not value
            ):
                self._process_current_time()

            return self.snapshot()

    def schedule_pending(self, result):
        if not isinstance(result, AlgorithmResult):
            raise ValueError(
                "result must be an AlgorithmResult."
            )

        scheduled_ids = tuple(
            result.schedule.task_order
        )

        if not scheduled_ids:
            raise ValueError(
                "The scheduling result contains no tasks."
            )

        with self._lock:
            if self._status not in {
                "CREATED",
                "RUNNING",
                "PAUSED",
            }:
                raise ValueError(
                    "Pending tasks cannot be scheduled "
                    "after the simulation has finished."
                )

            pending_ids = set(
                self._pending_task_ids
            )

            if (
                len(set(scheduled_ids))
                != len(scheduled_ids)
                or not set(scheduled_ids).issubset(
                    pending_ids
                )
            ):
                raise ValueError(
                    "The scheduling result must contain "
                    "only unique pending task IDs."
                )

            batch_tasks = [
                self._tasks[task_id].spec
                for task_id in scheduled_ids
            ]

            batch_problem = SchedulingProblem(
                batch_tasks,
                self.vm_specs(),
            )

            verified_schedule = (
                batch_problem.evaluate(
                    result.schedule.task_order
                )
            )

            if verified_schedule != result.schedule:
                raise ValueError(
                    "Algorithm result does not match "
                    "the pending task batch."
                )

            assignment_map = {
                assignment.task_id: assignment.vm_id
                for assignment
                in result.schedule.assignments
            }

            for task_id in scheduled_ids:
                task = self._tasks[task_id]

                task.vm_id = assignment_map[
                    task_id
                ]
                task.status = "WAITING"

                self._dispatch_order.append(
                    task_id
                )

            scheduled_set = set(
                scheduled_ids
            )

            self._pending_task_ids = deque(
                task_id
                for task_id
                in self._pending_task_ids
                if task_id not in scheduled_set
            )

            if self._status == "RUNNING":
                self._process_current_time()

            return self.snapshot()

    def start(self):
        with self._lock:
            if self._status != "CREATED":
                raise ValueError(
                    "Only a created simulation can start."
                )

            self._status = "RUNNING"

            try:
                self._process_current_time()
            except Exception as exc:
                self._mark_failed(exc)
                raise

            return self.snapshot()

    def advance(self, seconds):
        seconds = validate_number(
            seconds,
            "seconds",
            allow_zero=True,
        )

        with self._lock:
            if self._status == "CREATED":
                raise ValueError(
                    "Start the simulation before advancing."
                )

            if self._status != "RUNNING":
                return self.snapshot()

            target = self._clock + seconds

            if not math.isfinite(target):
                raise ValueError(
                    "Requested simulation time "
                    "is too large."
                )

            try:
                while self._status == "RUNNING":
                    event_time = (
                        self._next_event_time()
                    )

                    if event_time is None:
                        if (
                            self._pending_task_ids
                            or self._workload_open
                        ):
                            self._clock = target
                            break

                        raise RuntimeError(
                            "Active simulation has no "
                            "executable events."
                        )

                    if event_time < self._clock:
                        raise RuntimeError(
                            "Simulation event would move "
                            "time backward."
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
                raise ValueError(
                    "Only a running simulation can pause."
                )

            self._status = "PAUSED"

            return self.snapshot()

    def resume(self):
        with self._lock:
            if self._status != "PAUSED":
                raise ValueError(
                    "Only a paused simulation can resume."
                )

            self._status = "RUNNING"

            try:
                self._process_current_time()
            except Exception as exc:
                self._mark_failed(exc)
                raise

            return self.snapshot()

    def stop(self):
        with self._lock:
            if self._status not in {
                "CREATED",
                "RUNNING",
                "PAUSED",
            }:
                raise ValueError(
                    "Only a created, running, or paused "
                    "simulation can stop."
                )

            self._status = "STOPPED"

            return self.snapshot()

    def reset(self):
        with self._lock:
            if self._status not in {
                "COMPLETED",
                "STOPPED",
                "FAILED",
            }:
                raise ValueError(
                    "Stop or finish the simulation "
                    "before resetting."
                )

            return SimulationEngine(
                self.problem,
                self.result,
                dict(self.overload_thresholds),
                enable_redistribution=(
                    self.enable_redistribution
                ),
            )

    def snapshot(self):
        with self._lock:
            task_records = []

            for task in self._tasks.values():
                remaining_work = (
                    task.spec.work_mi
                )

                if task.status == "COMPLETED":
                    remaining_work = 0.0

                elif task.started_at is not None:
                    capacity = self._vms[
                        task.vm_id
                    ].spec.capacity_mips

                    remaining_work = max(
                        0.0,
                        task.spec.work_mi
                        - capacity
                        * (
                            self._clock
                            - task.started_at
                        ),
                    )

                task_records.append({
                    "id": task.spec.id,
                    "work_mi": task.spec.work_mi,
                    "arrival_time": (
                        task.spec.arrival_time
                    ),
                    "vm_id": (
                        None
                        if task.status in {
                            "PENDING",
                            "WAITING",
                        }
                        else task.vm_id
                    ),
                    "status": task.status,
                    "assigned_at": (
                        task.assigned_at
                    ),
                    "started_at": (
                        task.started_at
                    ),
                    "completed_at": (
                        task.completed_at
                    ),
                    "remaining_work_mi": (
                        remaining_work
                    ),
                })

            vm_records = [
                {
                    "id": vm.spec.id,
                    "capacity_mips": (
                        vm.spec.capacity_mips
                    ),
                    "overload_threshold": (
                        vm.overload_threshold
                    ),
                    "status": vm.status(
                        self._tasks,
                        self._status,
                    ),
                    "current_task_id": (
                        vm.current_task_id
                    ),
                    "queued_task_ids": list(
                        vm.queue
                    ),
                    "queued_seconds": (
                        vm.queued_seconds(
                            self._tasks
                        )
                    ),
                    "busy_seconds": (
                        vm.busy_seconds(
                            self._tasks,
                            self._clock,
                        )
                    ),
                }
                for vm in self._vms.values()
            ]

            pending_ids = list(
                self._pending_task_ids
            )

            return {
                "status": self._status,
                "simulated_time": self._clock,
                "algorithm": (
                    self.result.algorithm
                ),
                "algorithm_execution_seconds": (
                    self.result.execution_seconds
                ),
                "seed": self.result.seed,
                "initial_overload_thresholds": dict(
                    self.overload_thresholds
                ),
                "redistribution_enabled": (
                    self.enable_redistribution
                ),
                "redistribution_count": len(
                    self._redistributions
                ),
                "redistributions": [
                    dict(migration)
                    for migration
                    in self._redistributions
                ],
                "error": self._error,
                "tasks": task_records,
                "vms": vm_records,
                "workload_open": (
                    self._workload_open
                ),
                "pending_task_ids": pending_ids,
                "pending_tasks": len(
                    pending_ids
                ),
                "pending_work_mi": sum(
                    self._tasks[
                        task_id
                    ].spec.work_mi
                    for task_id in pending_ids
                ),
                "completed_tasks": sum(
                    task.status == "COMPLETED"
                    for task
                    in self._tasks.values()
                ),
                "running_tasks": sum(
                    task.status == "RUNNING"
                    for task
                    in self._tasks.values()
                ),
                "total_tasks": len(
                    self._tasks
                ),
            }