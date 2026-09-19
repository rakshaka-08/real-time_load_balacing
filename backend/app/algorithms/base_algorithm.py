import math
import random

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable


def validate_number(value, field, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number.")

    try:
        number = float(value)
    except OverflowError:
        raise ValueError(f"{field} is too large.") from None

    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite.")

    if number < 0 or (number == 0 and not allow_zero):
        requirement = "zero or greater" if allow_zero else "greater than zero"
        raise ValueError(f"{field} must be {requirement}.")

    return number


def validate_identifier(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string.")
    return value


@dataclass(frozen=True)
class TaskSpec:
    id: str
    work_mi: float
    arrival_time: float = 0.0

    def __post_init__(self):
        validate_identifier(self.id, "Task ID")
        object.__setattr__(
            self,
            "work_mi",
            validate_number(self.work_mi, "work_mi"),
        )
        object.__setattr__(
            self,
            "arrival_time",
            validate_number(
                self.arrival_time,
                "arrival_time",
                allow_zero=True,
            ),
        )


@dataclass(frozen=True)
class VMSpec:
    id: str
    capacity_mips: float

    def __post_init__(self):
        validate_identifier(self.id, "VM ID")
        object.__setattr__(
            self,
            "capacity_mips",
            validate_number(self.capacity_mips, "capacity_mips"),
        )


@dataclass(frozen=True)
class TaskAssignment:
    task_id: str
    vm_id: str
    arrival_time: float
    start_time: float
    finish_time: float
    execution_time: float

    @property
    def waiting_time(self):
        return self.start_time - self.arrival_time

    @property
    def response_time(self):
        return self.finish_time - self.arrival_time


@dataclass(frozen=True)
class ScheduleEvaluation:
    task_order: tuple[str, ...]
    assignments: tuple[TaskAssignment, ...]
    total_response_time: float
    makespan: float

    @property
    def fitness(self):
        # Lexicographic minimization:
        # response time first, makespan second.
        return self.total_response_time, self.makespan


@dataclass(frozen=True)
class AlgorithmResult:
    algorithm: str
    schedule: ScheduleEvaluation
    execution_seconds: float
    iterations: int
    seed: int


class SchedulingProblem:
    def __init__(
        self,
        tasks: Iterable[TaskSpec],
        vms: Iterable[VMSpec],
    ):
        self.tasks = tuple(tasks)
        self.vms = tuple(vms)

        if not all(isinstance(task, TaskSpec) for task in self.tasks):
            raise ValueError("All tasks must be TaskSpec objects.")

        if not self.vms or not all(
            isinstance(vm, VMSpec) for vm in self.vms
        ):
            raise ValueError("Supply at least one valid VMSpec.")

        self.task_ids = tuple(task.id for task in self.tasks)

        if len(set(self.task_ids)) != len(self.task_ids):
            raise ValueError("Task IDs must be unique.")

        vm_ids = tuple(vm.id for vm in self.vms)
        if len(set(vm_ids)) != len(vm_ids):
            raise ValueError("VM IDs must be unique.")

    def evaluate(self, task_order):
        order = tuple(task_order)

        if (
            not all(isinstance(task_id, str) for task_id in order)
            or len(order) != len(self.task_ids)
            or set(order) != set(self.task_ids)
        ):
            raise ValueError(
                "Candidate must contain every task ID exactly once."
            )

        priority = {
            task_id: position
            for position, task_id in enumerate(order)
        }

        dispatch_order = sorted(
            self.tasks,
            key=lambda task: (
                task.arrival_time,
                priority[task.id],
            ),
        )

        available_at = {vm.id: 0.0 for vm in self.vms}
        assignments = []

        for task in dispatch_order:
            options = []

            for vm in self.vms:
                duration = task.work_mi / vm.capacity_mips
                start = max(task.arrival_time, available_at[vm.id])
                finish = start + duration

                if (
                    not math.isfinite(duration)
                    or duration <= 0
                    or not math.isfinite(finish)
                    or finish <= start
                ):
                    raise ValueError(
                        "Task and VM values exceed supported timing precision."
                    )

                options.append(
                    (finish, start, vm.id, duration)
                )

            finish, start, vm_id, duration = min(options)

            assignments.append(
                TaskAssignment(
                    task_id=task.id,
                    vm_id=vm_id,
                    arrival_time=task.arrival_time,
                    start_time=start,
                    finish_time=finish,
                    execution_time=duration,
                )
            )
            available_at[vm_id] = finish

        try:
            total_response_time = math.fsum(
                assignment.response_time
                for assignment in assignments
            )
        except OverflowError:
            raise ValueError(
                "Total response time exceeds supported numeric range."
            ) from None

        if not math.isfinite(total_response_time):
            raise ValueError("Total response time must be finite.")

        # Simulation starts at time zero, including any initial idle time.
        makespan = max(
            (assignment.finish_time for assignment in assignments),
            default=0.0,
        )

        return ScheduleEvaluation(
            task_order=order,
            assignments=tuple(assignments),
            total_response_time=total_response_time,
            makespan=makespan,
        )


class BaseAlgorithm(ABC):
    def __init__(self, problem, seed=42):
        if not isinstance(problem, SchedulingProblem):
            raise ValueError("problem must be a SchedulingProblem.")

        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer.")

        if not 0 <= seed <= 2**32 - 1:
            raise ValueError("seed must be between 0 and 4294967295.")

        self.problem = problem
        self.seed = seed
        self.rng = random.Random(seed)

    def random_order(self):
        order = list(self.problem.task_ids)
        self.rng.shuffle(order)
        return tuple(order)

    def evaluate(self, task_order):
        return self.problem.evaluate(task_order)

    @abstractmethod
    def optimize(self) -> AlgorithmResult:
        """Return the algorithm's best schedule and execution metadata."""
        raise NotImplementedError