import unittest
from unittest.mock import patch

from app.algorithms.base_algorithm import (
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.algorithms.honey_bee_algorithm import HoneyBeeAlgorithm


class HoneyBeeAlgorithmTests(unittest.TestCase):
    def setUp(self):
        self.problem = SchedulingProblem(
            tasks=[
                TaskSpec("a", 1200),
                TaskSpec("b", 300),
                TaskSpec("c", 800),
                TaskSpec("d", 150),
                TaskSpec("e", 2000),
                TaskSpec("f", 450),
            ],
            vms=[
                VMSpec("slow", 250),
                VMSpec("medium", 500),
                VMSpec("fast", 1000),
            ],
        )

    def make_algorithm(self, **overrides):
        settings = {
            "seed": 42,
            "scout_bees": 10,
            "iterations": 12,
            "selected_sites": 4,
            "elite_sites": 2,
            "elite_recruits": 5,
            "other_recruits": 3,
            "neighborhood_moves": 1,
        }
        settings.update(overrides)
        return HoneyBeeAlgorithm(self.problem, **settings)

    def test_returns_valid_complete_schedule(self):
        result = self.make_algorithm().optimize()

        self.assertEqual(result.algorithm, "HBA")
        self.assertEqual(result.iterations, 12)
        self.assertEqual(result.seed, 42)
        self.assertGreaterEqual(result.execution_seconds, 0)

        assigned_ids = [
            assignment.task_id
            for assignment in result.schedule.assignments
        ]

        self.assertCountEqual(assigned_ids, self.problem.task_ids)
        self.assertEqual(len(set(assigned_ids)), len(assigned_ids))

        expected = self.problem.evaluate(result.schedule.task_order)
        self.assertEqual(result.schedule, expected)

    def test_same_seed_reproduces_schedule(self):
        first = self.make_algorithm(seed=123).optimize()
        second = self.make_algorithm(seed=123).optimize()

        self.assertEqual(first.schedule, second.schedule)

    def test_repeated_run_resets_search_state(self):
        algorithm = self.make_algorithm()

        first = algorithm.optimize()
        first_history = tuple(algorithm.best_fitness_history)

        second = algorithm.optimize()

        self.assertEqual(first.schedule, second.schedule)
        self.assertEqual(
            first_history,
            tuple(algorithm.best_fitness_history),
        )

    def test_best_fitness_never_worsens(self):
        algorithm = self.make_algorithm()
        result = algorithm.optimize()
        history = algorithm.best_fitness_history

        self.assertEqual(len(history), algorithm.iterations + 1)

        for previous, current in zip(history, history[1:]):
            self.assertLessEqual(current, previous)

        self.assertEqual(history[-1], result.schedule.fitness)

    def test_retains_at_least_input_order_quality(self):
        baseline = self.problem.evaluate(self.problem.task_ids)
        result = self.make_algorithm().optimize()

        self.assertLessEqual(
            result.schedule.fitness,
            baseline.fitness,
        )

    def test_neighbors_preserve_every_task(self):
        algorithm = self.make_algorithm(neighborhood_moves=3)
        original = self.problem.task_ids

        for _ in range(100):
            neighbor = algorithm._neighbor(original)

            self.assertEqual(len(neighbor), len(original))
            self.assertCountEqual(neighbor, original)
            self.assertEqual(len(set(neighbor)), len(original))

    def test_single_move_changes_order(self):
        algorithm = self.make_algorithm(neighborhood_moves=1)
        original = self.problem.task_ids

        for _ in range(50):
            self.assertNotEqual(
                algorithm._neighbor(original),
                original,
            )

    def test_neighborhood_search_does_not_worsen_site(self):
        algorithm = self.make_algorithm()
        site = self.problem.evaluate(self.problem.task_ids)

        winner = algorithm._search_site(
            site,
            recruits=20,
            evaluate=algorithm.evaluate,
        )

        self.assertLessEqual(winner.fitness, site.fitness)

    def test_random_scouts_are_used_each_iteration(self):
        algorithm = self.make_algorithm()

        with patch.object(
            algorithm,
            "random_order",
            wraps=algorithm.random_order,
        ) as random_order:
            algorithm.optimize()

        expected_calls = (
            algorithm.scout_bees - 1
            + algorithm.iterations
            * (algorithm.scout_bees - algorithm.selected_sites)
        )

        self.assertEqual(random_order.call_count, expected_calls)

    def test_recruitment_counts_match_site_ranking(self):
        algorithm = self.make_algorithm(iterations=1)

        with patch.object(
            algorithm,
            "_search_site",
            wraps=algorithm._search_site,
        ) as search:
            algorithm.optimize()

        recruit_counts = [
            call.args[1]
            for call in search.call_args_list
        ]

        self.assertEqual(recruit_counts, [5, 5, 3, 3])

    def test_empty_and_single_task_workloads(self):
        for tasks in ([], [TaskSpec("only", 1000)]):
            with self.subTest(task_count=len(tasks)):
                problem = SchedulingProblem(
                    tasks,
                    [VMSpec("vm", 500)],
                )
                algorithm = HoneyBeeAlgorithm(problem)
                result = algorithm.optimize()

                self.assertEqual(result.iterations, 0)
                self.assertEqual(
                    len(result.schedule.assignments),
                    len(tasks),
                )

                if tasks:
                    self.assertAlmostEqual(
                        result.schedule.makespan, 2.0
                    )
                else:
                    self.assertEqual(
                        result.schedule.fitness, (0.0, 0.0)
                    )

    def test_invalid_parameters_are_rejected(self):
        invalid_settings = [
            {"scout_bees": 1},
            {"scout_bees": True},
            {"iterations": 0},
            {"iterations": 1.5},
            {"selected_sites": 0},
            {"selected_sites": 10},
            {"elite_sites": 0},
            {"elite_sites": 5},
            {"elite_recruits": 0},
            {"elite_recruits": 2, "other_recruits": 3},
            {"other_recruits": 0},
            {"neighborhood_moves": 0},
            {"neighborhood_moves": True},
            {"seed": -1},
        ]

        for settings in invalid_settings:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    self.make_algorithm(**settings)

    def test_all_selected_sites_can_be_elite(self):
        algorithm = self.make_algorithm(elite_sites=4)
        result = algorithm.optimize()

        self.assertCountEqual(
            result.schedule.task_order,
            self.problem.task_ids,
        )
        self.assertEqual(result.iterations, 12)


if __name__ == "__main__":
    unittest.main()