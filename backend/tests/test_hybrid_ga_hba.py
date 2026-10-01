import unittest

from app.algorithms.base_algorithm import (
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.algorithms.genetic_algorithm import GeneticAlgorithm
from app.algorithms.hybrid_ga_hba import HybridGAHBAAlgorithm


class HybridGAHBATests(unittest.TestCase):
    def setUp(self):
        self.problem = SchedulingProblem(
            [
                TaskSpec("task-1", 900, 0),
                TaskSpec("task-2", 500, 0),
                TaskSpec("task-3", 250, 1),
                TaskSpec("task-4", 700, 2),
                TaskSpec("task-5", 300, 2),
            ],
            [
                VMSpec("vm-fast", 500),
                VMSpec("vm-medium", 250),
                VMSpec("vm-slow", 100),
            ],
        )

        self.parameters = {
            "population_size": 20,
            "generations": 15,
            "crossover_rate": 0.9,
            "mutation_rate": 0.15,
            "tournament_size": 3,
            "elite_count": 2,
            "scout_bees": 15,
            "hba_iterations": 15,
            "selected_sites": 5,
            "elite_sites": 2,
            "elite_recruits": 6,
            "other_recruits": 3,
            "neighborhood_moves": 1,
        }

    def test_returns_complete_valid_schedule(self):
        result = HybridGAHBAAlgorithm(
            self.problem,
            seed=42,
            **self.parameters,
        ).optimize()

        self.assertEqual(result.algorithm, "GA_HBA")
        self.assertEqual(
            set(result.schedule.task_order),
            set(self.problem.task_ids),
        )
        self.assertEqual(
            len(result.schedule.task_order),
            len(self.problem.task_ids),
        )
        self.assertEqual(result.iterations, 30)

    def test_same_seed_is_reproducible(self):
        first = HybridGAHBAAlgorithm(
            self.problem,
            seed=77,
            **self.parameters,
        ).optimize()

        second = HybridGAHBAAlgorithm(
            self.problem,
            seed=77,
            **self.parameters,
        ).optimize()

        self.assertEqual(
            first.schedule.task_order,
            second.schedule.task_order,
        )
        self.assertEqual(
            first.schedule.fitness,
            second.schedule.fitness,
        )

    def test_hybrid_is_not_worse_than_its_ga_phase(self):
        ga = GeneticAlgorithm(
            self.problem,
            seed=19,
            population_size=self.parameters["population_size"],
            generations=self.parameters["generations"],
            crossover_rate=self.parameters["crossover_rate"],
            mutation_rate=self.parameters["mutation_rate"],
            tournament_size=self.parameters["tournament_size"],
            elite_count=self.parameters["elite_count"],
        ).optimize()

        hybrid = HybridGAHBAAlgorithm(
            self.problem,
            seed=19,
            **self.parameters,
        ).optimize()

        self.assertLessEqual(
            hybrid.schedule.fitness,
            ga.schedule.fitness,
        )

    def test_invalid_hba_configuration_is_rejected(self):
        parameters = {
            **self.parameters,
            "selected_sites": 15,
        }

        with self.assertRaisesRegex(
            ValueError,
            "selected_sites must be smaller than scout_bees",
        ):
            HybridGAHBAAlgorithm(
                self.problem,
                seed=42,
                **parameters,
            )


if __name__ == "__main__":
    unittest.main()