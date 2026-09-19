import unittest

from app.algorithms.base_algorithm import (
    BaseAlgorithm,
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)


class AlgorithmFoundationTests(unittest.TestCase):
    def setUp(self):
        self.problem = SchedulingProblem(
            tasks=[
                TaskSpec("task-a", 1000),
                TaskSpec("task-b", 500),
            ],
            vms=[
                VMSpec("slow", 250),
                VMSpec("fast", 500),
            ],
        )

    def test_heterogeneous_assignment(self):
        result = self.problem.evaluate(("task-a", "task-b"))
        assignments = {
            item.task_id: item
            for item in result.assignments
        }

        self.assertEqual(assignments["task-a"].vm_id, "fast")
        self.assertEqual(assignments["task-b"].vm_id, "slow")
        self.assertAlmostEqual(result.total_response_time, 4.0)
        self.assertAlmostEqual(result.makespan, 2.0)

    def test_order_changes_schedule(self):
        result = self.problem.evaluate(("task-b", "task-a"))

        self.assertAlmostEqual(result.total_response_time, 4.0)
        self.assertAlmostEqual(result.makespan, 3.0)

    def test_fitness_uses_makespan_to_break_response_time_tie(self):
        first = self.problem.evaluate(("task-a", "task-b"))
        second = self.problem.evaluate(("task-b", "task-a"))

        self.assertLess(first.fitness, second.fitness)

    def test_arrivals_take_priority_over_candidate_order(self):
        problem = SchedulingProblem(
            tasks=[
                TaskSpec("later", 1000, arrival_time=10),
                TaskSpec("earlier", 500, arrival_time=0),
            ],
            vms=[VMSpec("vm", 500)],
        )

        result = problem.evaluate(("later", "earlier"))

        self.assertEqual(result.assignments[0].task_id, "earlier")
        self.assertEqual(result.assignments[1].start_time, 10)
        self.assertAlmostEqual(result.total_response_time, 3.0)
        self.assertAlmostEqual(result.makespan, 12.0)

    def test_waiting_time_and_no_overlap(self):
        problem = SchedulingProblem(
            tasks=[
                TaskSpec("first", 200),
                TaskSpec("second", 100),
            ],
            vms=[VMSpec("vm", 100)],
        )

        result = problem.evaluate(("first", "second"))
        first, second = result.assignments

        self.assertEqual(second.start_time, first.finish_time)
        self.assertAlmostEqual(second.waiting_time, 2.0)
        self.assertAlmostEqual(second.response_time, 3.0)
        self.assertAlmostEqual(result.total_response_time, 5.0)

    def test_vm_ties_are_deterministic(self):
        problem = SchedulingProblem(
            tasks=[TaskSpec("task", 100)],
            vms=[
                VMSpec("vm-b", 100),
                VMSpec("vm-a", 100),
            ],
        )

        result = problem.evaluate(("task",))
        self.assertEqual(result.assignments[0].vm_id, "vm-a")

    def test_invalid_permutations_are_rejected(self):
        invalid_orders = [
            ("task-a",),
            ("task-a", "task-a"),
            ("task-a", "unknown"),
            ("task-a", "task-b", "extra"),
        ]

        for order in invalid_orders:
            with self.subTest(order=order):
                with self.assertRaises(ValueError):
                    self.problem.evaluate(order)

    def test_invalid_numeric_inputs_are_rejected(self):
        for value in (0, -1, True, "100", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    TaskSpec("task", value)

                with self.assertRaises(ValueError):
                    VMSpec("vm", value)

        with self.assertRaises(ValueError):
            TaskSpec("task", 100, arrival_time=-1)

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            SchedulingProblem(
                [TaskSpec("same", 100), TaskSpec("same", 200)],
                [VMSpec("vm", 100)],
            )

        with self.assertRaises(ValueError):
            SchedulingProblem(
                [TaskSpec("task", 100)],
                [VMSpec("same", 100), VMSpec("same", 200)],
            )

    def test_no_vms_is_rejected(self):
        with self.assertRaises(ValueError):
            SchedulingProblem([TaskSpec("task", 100)], [])

    def test_empty_workload(self):
        problem = SchedulingProblem([], [VMSpec("vm", 100)])
        result = problem.evaluate(())

        self.assertEqual(result.assignments, ())
        self.assertEqual(result.fitness, (0.0, 0.0))

    def test_repeated_evaluation_does_not_keep_previous_load(self):
        first = self.problem.evaluate(("task-a", "task-b"))
        second = self.problem.evaluate(("task-a", "task-b"))

        self.assertEqual(first, second)

    def test_base_algorithm_is_abstract(self):
        with self.assertRaises(TypeError):
            BaseAlgorithm(self.problem)


if __name__ == "__main__":
    unittest.main()