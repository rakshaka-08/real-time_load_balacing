import math

from dataclasses import dataclass

from ..algorithms.base_algorithm import (
    BaseAlgorithm,
    SchedulingProblem,
    validate_number,
)
from .simulation_engine import SimulationEngine
from .task_generator import TaskGenerator


@dataclass(frozen=True)
class MicroBatchConfig:
    batch_size: int = 5
    batch_interval: float = 1.0
    seed: int = 42

    def __post_init__(self):
        if (
            isinstance(self.batch_size, bool)
            or not isinstance(self.batch_size, int)
            or not 1 <= self.batch_size <= 500
        ):
            raise ValueError(
                "batch_size must be an integer between 1 and 500."
            )

        batch_interval = validate_number(
            self.batch_interval,
            "batch_interval",
        )

        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer.")

        if not 0 <= self.seed <= 2**32 - 1:
            raise ValueError(
                "seed must be between 0 and 4294967295."
            )

        object.__setattr__(
            self,
            "batch_interval",
            batch_interval,
        )

    def to_dict(self):
        return {
            "batch_size": self.batch_size,
            "batch_interval": self.batch_interval,
            "seed": self.seed,
        }


class MicroBatchScheduler:
    def __init__(
        self,
        engine,
        generator,
        algorithm_class,
        config,
        algorithm_parameters=None,
    ):
        if not isinstance(engine, SimulationEngine):
            raise ValueError(
                "engine must be a SimulationEngine."
            )

        if not isinstance(generator, TaskGenerator):
            raise ValueError(
                "generator must be a TaskGenerator."
            )

        if not isinstance(config, MicroBatchConfig):
            raise ValueError(
                "config must be a MicroBatchConfig."
            )

        if (
            not isinstance(algorithm_class, type)
            or not issubclass(
                algorithm_class,
                BaseAlgorithm,
            )
        ):
            raise ValueError(
                "algorithm_class must extend BaseAlgorithm."
            )

        if algorithm_parameters is None:
            algorithm_parameters = {}

        if not isinstance(algorithm_parameters, dict):
            raise ValueError(
                "algorithm_parameters must be a dictionary."
            )

        self.engine = engine
        self.generator = generator
        self.algorithm_class = algorithm_class
        self.config = config
        self.algorithm_parameters = dict(
            algorithm_parameters
        )

        state = engine.snapshot()

        self._last_batch_time = state[
            "simulated_time"
        ]
        self._batch_count = 0
        self._scheduled_task_count = 0
        self._scheduler_execution_seconds = 0.0
        self._batch_history = []

        self.engine.set_workload_open(
            not self.generator.exhausted
        )

    @property
    def next_batch_time(self):
        return (
            self._last_batch_time
            + self.config.batch_interval
        )

    def _batch_seed(self):
        return (
            self.config.seed
            + self._batch_count
        ) % (2**32)

    def _schedule_batch(self, limit):
        tasks = self.engine.pending_task_specs(
            limit=limit
        )

        if not tasks:
            return None

        problem = SchedulingProblem(
            tasks,
            self.engine.vm_specs(),
        )

        algorithm = self.algorithm_class(
            problem,
            seed=self._batch_seed(),
            **self.algorithm_parameters,
        )

        result = algorithm.optimize()
        self.engine.schedule_pending(result)

        self._batch_count += 1
        self._scheduled_task_count += len(tasks)
        self._scheduler_execution_seconds += (
            result.execution_seconds
        )

        batch_record = {
            "batch_number": self._batch_count,
            "task_ids": [
                task.id
                for task in tasks
            ],
            "task_count": len(tasks),
            "algorithm": result.algorithm,
            "seed": result.seed,
            "execution_seconds": (
                result.execution_seconds
            ),
            "scheduled_at": self.engine.snapshot()[
                "simulated_time"
            ],
        }

        self._batch_history.append(batch_record)

        return batch_record

    def process_current_time(self):
        state = self.engine.snapshot()
        current_time = state["simulated_time"]

        generated = self.generator.generate_until(
            current_time
        )

        if generated:
            self.engine.add_tasks(generated)

        while (
            len(self.engine.pending_task_specs())
            >= self.config.batch_size
        ):
            self._schedule_batch(
                self.config.batch_size
            )

        interval_due = (
            current_time - self._last_batch_time
            >= self.config.batch_interval
        )

        if interval_due:
            pending_count = len(
                self.engine.pending_task_specs()
            )

            if pending_count:
                self._schedule_batch(
                    min(
                        pending_count,
                        self.config.batch_size,
                    )
                )

            self._last_batch_time = current_time

        if self.generator.exhausted:
            self.engine.set_workload_open(False)

        return {
            "generated_tasks": len(generated),
            "simulation": self.engine.snapshot(),
            "scheduler": self.snapshot(),
        }

    def advance(self, seconds):
        seconds = validate_number(
            seconds,
            "seconds",
            allow_zero=True,
        )

        state = self.engine.snapshot()

        if state["status"] != "RUNNING":
            raise ValueError(
                "Start the simulation before advancing "
                "the micro-batch scheduler."
            )

        target_time = (
            state["simulated_time"]
            + seconds
        )

        if not math.isfinite(target_time):
            raise ValueError(
                "Requested simulation time is too large."
            )

        self.process_current_time()

        while True:
            state = self.engine.snapshot()
            current_time = state["simulated_time"]

            if (
                current_time >= target_time
                or state["status"] != "RUNNING"
            ):
                break

            candidate_times = [target_time]

            next_arrival = (
                self.generator.next_arrival_time
            )

            if (
                next_arrival is not None
                and next_arrival > current_time
            ):
                candidate_times.append(
                    next_arrival
                )

            batch_time = self.next_batch_time

            if batch_time > current_time:
                candidate_times.append(
                    batch_time
                )

            next_time = min(candidate_times)

            if next_time <= current_time:
                next_time = target_time

            self.engine.advance(
                next_time - current_time
            )
            self.process_current_time()

        return {
            "simulation": self.engine.snapshot(),
            "scheduler": self.snapshot(),
        }

    def snapshot(self):
        return {
            "configuration": self.config.to_dict(),
            "algorithm": self.algorithm_class.__name__,
            "algorithm_parameters": dict(
                self.algorithm_parameters
            ),
            "batch_count": self._batch_count,
            "scheduled_task_count": (
                self._scheduled_task_count
            ),
            "scheduler_execution_seconds": (
                self._scheduler_execution_seconds
            ),
            "last_batch_time": self._last_batch_time,
            "next_batch_time": self.next_batch_time,
            "batches": [
                dict(batch)
                for batch in self._batch_history
            ],
            "generator": self.generator.snapshot(),
        }