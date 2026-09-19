import unittest

from app.algorithms.base_algorithm import (
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.algorithms.spt import SPTAlgorithm


class SPTTests(unittest.TestCase):
    def setUp(self):
        self.problem = SchedulingProblem(
            tasks=[
                TaskSpec("b", 500),
                TaskSpec("a", 1000),
                TaskSpec("c", 250),
            ],
            vms=[
                VMSpec("slow", 250),
                VMSpec("fast", 500),
            ],
        )

    def test_shortest_tasks_first(self):
        result = SPTAlgorithm(self.problem).optimize()

        self.assertEqual(
            result.schedule.task_order,
            ("c", "b", "a"),
        )
        self.assertEqual(result.algorithm, "SPT")
        self.assertEqual(result.iterations, 1)
        self.assertGreaterEqual(result.execution_seconds, 0)

    def test_known_heterogeneous_schedule(self):
        result = SPTAlgorithm(self.problem).optimize()
        assignments = result.schedule.assignments

        self.assertEqual(
            [item.vm_id for item in assignments],
            ["fast", "fast", "slow"],
        )
        self.assertAlmostEqual(
            result.schedule.total_response_time, 6.0
        )
        self.assertAlmostEqual(result.schedule.makespan, 4.0)

    def test_equal_lengths_use_task_id(self):
        problem = SchedulingProblem(
            [TaskSpec("z", 100), TaskSpec("a", 100)],
            [VMSpec("vm", 100)],
        )

        result = SPTAlgorithm(problem).optimize()
        self.assertEqual(result.schedule.task_order, ("a", "z"))

    def test_future_task_does_not_delay_earlier_arrival(self):
        problem = SchedulingProblem(
            [
                TaskSpec("later-short", 100, arrival_time=10),
                TaskSpec("earlier-long", 1000, arrival_time=0),
            ],
            [VMSpec("vm", 500)],
        )

        result = SPTAlgorithm(problem).optimize()
        first, second = result.schedule.assignments

        self.assertEqual(first.task_id, "earlier-long")
        self.assertEqual(first.start_time, 0)
        self.assertEqual(second.task_id, "later-short")
        self.assertEqual(second.start_time, 10)

    def test_empty_workload(self):
        problem = SchedulingProblem([], [VMSpec("vm", 500)])
        result = SPTAlgorithm(problem).optimize()

        self.assertEqual(result.schedule.assignments, ())
        self.assertEqual(result.schedule.fitness, (0.0, 0.0))
        self.assertEqual(result.iterations, 0)

    def test_single_task(self):
        problem = SchedulingProblem(
            [TaskSpec("only", 1000)],
            [VMSpec("vm", 500)],
        )

        result = SPTAlgorithm(problem).optimize()

        self.assertAlmostEqual(result.schedule.makespan, 2.0)
        self.assertAlmostEqual(
            result.schedule.total_response_time, 2.0
        )

    def test_seed_does_not_change_schedule(self):
        first = SPTAlgorithm(self.problem, seed=1).optimize()
        second = SPTAlgorithm(self.problem, seed=999).optimize()

        self.assertEqual(first.schedule, second.schedule)

    def test_every_task_is_assigned_once(self):
        result = SPTAlgorithm(self.problem).optimize()
        assigned_ids = [
            item.task_id
            for item in result.schedule.assignments
        ]

        self.assertCountEqual(assigned_ids, self.problem.task_ids)
        self.assertEqual(len(assigned_ids), len(set(assigned_ids)))
        self.assertEqual(
            result.schedule,
            self.problem.evaluate(result.schedule.task_order),
        )


if __name__ == "__main__":
    unittest.main()