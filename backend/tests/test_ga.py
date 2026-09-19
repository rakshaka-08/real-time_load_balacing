import unittest

from app.algorithms.base_algorithm import (
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.algorithms.genetic_algorithm import GeneticAlgorithm


class GeneticAlgorithmTests(unittest.TestCase):
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
            "population_size": 12,
            "generations": 15,
            "tournament_size": 3,
            "elite_count": 2,
        }
        settings.update(overrides)
        return GeneticAlgorithm(self.problem, **settings)

    def test_returns_valid_complete_schedule(self):
        result = self.make_algorithm().optimize()

        self.assertEqual(result.algorithm, "GA")
        self.assertEqual(result.iterations, 15)
        self.assertEqual(result.seed, 42)
        self.assertGreaterEqual(result.execution_seconds, 0)

        assigned_ids = [
            assignment.task_id
            for assignment in result.schedule.assignments
        ]

        self.assertCountEqual(assigned_ids, self.problem.task_ids)
        self.assertEqual(len(set(assigned_ids)), len(assigned_ids))

        # Returned fitness must match an independent reevaluation.
        expected = self.problem.evaluate(result.schedule.task_order)
        self.assertEqual(result.schedule, expected)

    def test_same_seed_reproduces_schedule(self):
        first = self.make_algorithm(seed=123).optimize()
        second = self.make_algorithm(seed=123).optimize()

        self.assertEqual(first.schedule, second.schedule)
        # Wall-clock runtime is intentionally not compared.

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

        self.assertEqual(len(history), algorithm.generations + 1)

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

    def test_crossover_preserves_each_task_exactly_once(self):
        algorithm = self.make_algorithm(crossover_rate=1.0)
        first = self.problem.task_ids
        second = tuple(reversed(first))

        for _ in range(100):
            children = algorithm._crossover(first, second)

            for child in children:
                self.assertEqual(len(child), len(first))
                self.assertCountEqual(child, first)
                self.assertEqual(len(set(child)), len(first))

    def test_ordered_crossover_retains_segment_and_donor_order(self):
        child = GeneticAlgorithm._ordered_child(
            ("a", "b", "c", "d", "e", "f"),
            ("f", "e", "d", "c", "b", "a"),
            1,
            3,
        )

        self.assertEqual(child, ("d", "b", "c", "a", "f", "e"))

    def test_mutation_swaps_two_positions(self):
        algorithm = self.make_algorithm(mutation_rate=1.0)
        original = self.problem.task_ids
        mutated = algorithm._mutate(original)

        self.assertCountEqual(mutated, original)
        changed_positions = sum(
            before != after
            for before, after in zip(original, mutated)
        )
        self.assertEqual(changed_positions, 2)

    def test_zero_rates_leave_parents_unchanged(self):
        algorithm = self.make_algorithm(
            crossover_rate=0.0,
            mutation_rate=0.0,
        )
        first = self.problem.task_ids
        second = tuple(reversed(first))

        self.assertEqual(
            algorithm._crossover(first, second),
            (first, second),
        )
        self.assertEqual(algorithm._mutate(first), first)

    def test_tournament_selects_best_when_all_compete(self):
        algorithm = self.make_algorithm(tournament_size=3)
        orders = [
            self.problem.task_ids,
            tuple(reversed(self.problem.task_ids)),
            ("b", "d", "f", "c", "a", "e"),
        ]
        evaluations = [
            self.problem.evaluate(order)
            for order in orders
        ]

        selected = algorithm._select_parent(evaluations)
        selected_fitness = self.problem.evaluate(selected).fitness

        self.assertEqual(
            selected_fitness,
            min(item.fitness for item in evaluations),
        )

    def test_empty_and_single_task_workloads(self):
        for tasks in ([], [TaskSpec("only", 1000)]):
            with self.subTest(task_count=len(tasks)):
                problem = SchedulingProblem(
                    tasks,
                    [VMSpec("vm", 500)],
                )
                algorithm = GeneticAlgorithm(problem)
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
            {"population_size": 1},
            {"population_size": True},
            {"generations": 0},
            {"generations": 1.5},
            {"tournament_size": 0},
            {"tournament_size": 13},
            {"elite_count": 0},
            {"elite_count": 12},
            {"crossover_rate": -0.1},
            {"crossover_rate": 1.1},
            {"mutation_rate": float("nan")},
            {"mutation_rate": True},
            {"seed": -1},
        ]

        for settings in invalid_settings:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    self.make_algorithm(**settings)

    def test_odd_population_size(self):
        algorithm = self.make_algorithm(population_size=7)
        result = algorithm.optimize()

        self.assertCountEqual(
            result.schedule.task_order,
            self.problem.task_ids,
        )
        self.assertEqual(result.iterations, 15)


if __name__ == "__main__":
    unittest.main()