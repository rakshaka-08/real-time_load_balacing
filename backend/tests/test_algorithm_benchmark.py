import unittest

from app.algorithms.base_algorithm import (
    AlgorithmResult,
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.simulation.benchmark import (
    BENCHMARK_ALGORITHMS,
    benchmark_algorithms,
)


class StubAlgorithm:
    def __init__(
        self,
        problem,
        name,
        seed,
        reverse=False,
    ):
        self.problem = problem
        self.name = name
        self.seed = seed
        self.reverse = reverse

    def optimize(self):
        task_order = tuple(
            self.problem.task_ids
        )

        if self.reverse:
            task_order = tuple(
                reversed(task_order)
            )

        schedule = self.problem.evaluate(
            task_order
        )

        return AlgorithmResult(
            algorithm=self.name,
            schedule=schedule,
            execution_seconds=0.001,
            iterations=1,
            seed=self.seed,
        )


def make_factory(name, calls):
    def factory(
        problem,
        seed=42,
        reverse=False,
    ):
        calls.append({
            "name": name,
            "problem": problem,
            "seed": seed,
            "reverse": reverse,
        })

        return StubAlgorithm(
            problem,
            name,
            seed,
            reverse=reverse,
        )

    return factory


class AlgorithmBenchmarkTests(
    unittest.TestCase
):
    def setUp(self):
        self.problem = SchedulingProblem(
            [
                TaskSpec(
                    "task-1",
                    100.0,
                    0.0,
                ),
                TaskSpec(
                    "task-2",
                    200.0,
                    0.5,
                ),
            ],
            [
                VMSpec("vm-1", 100.0),
                VMSpec("vm-2", 50.0),
            ],
        )

        self.thresholds = {
            "vm-1": 10.0,
            "vm-2": 10.0,
        }

        self.calls = []

        self.algorithm_types = {
            name: make_factory(
                name,
                self.calls,
            )
            for name in BENCHMARK_ALGORITHMS
        }

    def run_benchmark(self, **overrides):
        arguments = {
            "problem": self.problem,
            "overload_thresholds": (
                self.thresholds
            ),
            "algorithm_types": (
                self.algorithm_types
            ),
            "seed": 77,
        }
        arguments.update(overrides)

        return benchmark_algorithms(
            **arguments
        )

    def test_runs_every_supported_algorithm(self):
        result = self.run_benchmark()

        self.assertEqual(
            [
                row["algorithm"]
                for row in result["algorithms"]
            ],
            list(BENCHMARK_ALGORITHMS),
        )

    def test_every_algorithm_receives_same_workload(self):
        self.run_benchmark()

        self.assertEqual(
            len(self.calls),
            len(BENCHMARK_ALGORITHMS),
        )

        self.assertTrue(
            all(
                call["problem"]
                is self.problem
                for call in self.calls
            )
        )

    def test_every_algorithm_receives_same_seed(self):
        self.run_benchmark()

        self.assertEqual(
            {
                call["seed"]
                for call in self.calls
            },
            {77},
        )

    def test_results_contain_actual_metrics(self):
        result = self.run_benchmark()

        for row in result["algorithms"]:
            self.assertIn(
                "system_utilization",
                row,
            )
            self.assertIn(
                "total_response_time",
                row,
            )
            self.assertIn(
                "average_response_time",
                row,
            )
            self.assertIn(
                "makespan",
                row,
            )
            self.assertIn(
                "load_imbalance",
                row,
            )
            self.assertIn(
                "scheduler_execution_seconds",
                row,
            )
            self.assertIn(
                "redistribution_count",
                row,
            )

    def test_parameters_are_isolated_by_algorithm(self):
        self.run_benchmark(
            parameters={
                "GA": {
                    "reverse": True,
                }
            }
        )

        ga_call = next(
            call
            for call in self.calls
            if call["name"] == "GA"
        )

        hba_call = next(
            call
            for call in self.calls
            if call["name"] == "HBA"
        )

        self.assertTrue(
            ga_call["reverse"]
        )
        self.assertFalse(
            hba_call["reverse"]
        )

    def test_missing_algorithm_is_rejected(self):
        incomplete = dict(
            self.algorithm_types
        )
        incomplete.pop("SPT")

        with self.assertRaisesRegex(
            ValueError,
            "Missing benchmark algorithms",
        ):
            self.run_benchmark(
                algorithm_types=incomplete
            )

    def test_invalid_seed_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "seed must be an integer",
        ):
            self.run_benchmark(seed=True)


if __name__ == "__main__":
    unittest.main()