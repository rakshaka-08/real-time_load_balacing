import math
import random

from dataclasses import dataclass

from ..algorithms.base_algorithm import (
    TaskSpec,
    validate_identifier,
    validate_number,
)


MAX_GENERATED_TASKS = 100_000


@dataclass(frozen=True)
class TaskGeneratorConfig:
    arrival_rate: float
    min_work_mi: float
    max_work_mi: float
    seed: int = 42
    max_tasks: int = 10_000
    start_time: float = 0.0
    task_id_prefix: str = "live"

    def __post_init__(self):
        arrival_rate = validate_number(
            self.arrival_rate,
            "arrival_rate",
        )
        min_work_mi = validate_number(
            self.min_work_mi,
            "min_work_mi",
        )
        max_work_mi = validate_number(
            self.max_work_mi,
            "max_work_mi",
        )
        start_time = validate_number(
            self.start_time,
            "start_time",
            allow_zero=True,
        )

        if min_work_mi > max_work_mi:
            raise ValueError(
                "min_work_mi must be less than or equal to max_work_mi."
            )

        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer.")

        if not 0 <= self.seed <= 2**32 - 1:
            raise ValueError(
                "seed must be between 0 and 4294967295."
            )

        if (
            isinstance(self.max_tasks, bool)
            or not isinstance(self.max_tasks, int)
            or not 1 <= self.max_tasks <= MAX_GENERATED_TASKS
        ):
            raise ValueError(
                "max_tasks must be an integer between "
                f"1 and {MAX_GENERATED_TASKS}."
            )

        task_id_prefix = validate_identifier(
            self.task_id_prefix,
            "task_id_prefix",
        ).strip()

        if len(task_id_prefix) > 40:
            raise ValueError(
                "task_id_prefix must contain at most 40 characters."
            )

        object.__setattr__(self, "arrival_rate", arrival_rate)
        object.__setattr__(self, "min_work_mi", min_work_mi)
        object.__setattr__(self, "max_work_mi", max_work_mi)
        object.__setattr__(self, "start_time", start_time)
        object.__setattr__(
            self,
            "task_id_prefix",
            task_id_prefix,
        )

    def to_dict(self):
        return {
            "arrival_rate": self.arrival_rate,
            "min_work_mi": self.min_work_mi,
            "max_work_mi": self.max_work_mi,
            "seed": self.seed,
            "max_tasks": self.max_tasks,
            "start_time": self.start_time,
            "task_id_prefix": self.task_id_prefix,
        }


class TaskGenerator:
    """
    Deterministically generates tasks as simulated time advances.

    Inter-arrival times use an exponential distribution. The configured
    arrival_rate represents the expected number of tasks per simulated
    second.
    """

    def __init__(self, config):
        if not isinstance(config, TaskGeneratorConfig):
            raise ValueError(
                "config must be a TaskGeneratorConfig."
            )

        self.config = config
        self._rng = random.Random(config.seed)
        self._generated_count = 0
        self._last_requested_time = 0.0
        self._next_arrival_time = self._sample_arrival_after(
            config.start_time
        )

    @property
    def generated_count(self):
        return self._generated_count

    @property
    def next_arrival_time(self):
        return self._next_arrival_time

    @property
    def exhausted(self):
        return self._generated_count >= self.config.max_tasks

    def _sample_arrival_after(self, current_time):
        interval = self._rng.expovariate(
            self.config.arrival_rate
        )
        arrival_time = current_time + interval

        if not math.isfinite(arrival_time):
            raise ValueError(
                "Generated arrival time exceeds the supported range."
            )

        return arrival_time

    def _sample_work(self):
        work_mi = self._rng.uniform(
            self.config.min_work_mi,
            self.config.max_work_mi,
        )

        if not math.isfinite(work_mi) or work_mi <= 0:
            raise ValueError(
                "Generated task work exceeds the supported range."
            )

        return work_mi

    def _next_task_id(self):
        sequence = self._generated_count + 1

        return (
            f"{self.config.task_id_prefix}-"
            f"{sequence:06d}"
        )

    def generate_until(self, simulated_time):
        target_time = validate_number(
            simulated_time,
            "simulated_time",
            allow_zero=True,
        )

        if target_time < self._last_requested_time:
            raise ValueError(
                "simulated_time cannot move backward."
            )

        generated = []

        while (
            not self.exhausted
            and self._next_arrival_time is not None
            and self._next_arrival_time <= target_time
        ):
            arrival_time = self._next_arrival_time
            task_id = self._next_task_id()
            work_mi = self._sample_work()

            generated.append(
                TaskSpec(
                    id=task_id,
                    work_mi=work_mi,
                    arrival_time=arrival_time,
                )
            )

            self._generated_count += 1

            if self.exhausted:
                self._next_arrival_time = None
            else:
                self._next_arrival_time = (
                    self._sample_arrival_after(arrival_time)
                )

        self._last_requested_time = target_time

        return tuple(generated)

    def snapshot(self):
        return {
            "configuration": self.config.to_dict(),
            "generated_count": self.generated_count,
            "next_arrival_time": self.next_arrival_time,
            "last_requested_time": self._last_requested_time,
            "exhausted": self.exhausted,
        }