from time import perf_counter

from .base_algorithm import AlgorithmResult, BaseAlgorithm


class LPTAlgorithm(BaseAlgorithm):
    def optimize(self):
        started = perf_counter()

        ordered_tasks = sorted(
            self.problem.tasks,
            key=lambda task: (-task.work_mi, task.id),
        )
        order = tuple(task.id for task in ordered_tasks)
        schedule = self.evaluate(order)

        return AlgorithmResult(
            algorithm="LPT",
            schedule=schedule,
            execution_seconds=perf_counter() - started,
            iterations=1 if order else 0,
            seed=self.seed,
        )