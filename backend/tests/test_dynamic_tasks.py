import unittest

from app.algorithms.base_algorithm import (
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.algorithms.lpt import LPTAlgorithm
from app.simulation.simulation_engine import (
    SimulationEngine,
)


class DynamicTaskTests(unittest.TestCase):
    def make_engine(self):
        problem = SchedulingProblem(
            [
                TaskSpec(
                    "initial",
                    100,
                    arrival_time=0,
                ),
            ],
            [
                VMSpec("vm-a", 100),
                VMSpec("vm-b", 200),
            ],
        )

        result = LPTAlgorithm(problem).optimize()

        return SimulationEngine(
            problem,
            result,
            {
                "vm-a": 10,
                "vm-b": 10,
            },
        )

    def schedule(self, engine, tasks):
        problem = SchedulingProblem(
            tasks,
            [
                VMSpec("vm-a", 100),
                VMSpec("vm-b", 200),
            ],
        )

        result = LPTAlgorithm(problem).optimize()
        return engine.schedule_pending(result)

    def test_added_tasks_enter_pending_queue(self):
        engine = self.make_engine()
        engine.start()

        state = engine.add_tasks([
            TaskSpec("live-1", 250, arrival_time=0),
            TaskSpec("live-2", 300, arrival_time=0),
        ])

        self.assertEqual(state["pending_tasks"], 2)
        self.assertEqual(state["pending_work_mi"], 550)
        self.assertEqual(
            state["pending_task_ids"],
            ["live-1", "live-2"],
        )

        tasks = {
            task["id"]: task
            for task in state["tasks"]
        }

        self.assertEqual(
            tasks["live-1"]["status"],
            "PENDING",
        )
        self.assertIsNone(tasks["live-1"]["vm_id"])

    def test_duplicate_ids_are_rejected_atomically(self):
        engine = self.make_engine()
        engine.start()

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            engine.add_tasks([
                TaskSpec("new-task", 100),
                TaskSpec("initial", 100),
            ])

        state = engine.snapshot()

        self.assertNotIn(
            "new-task",
            {
                task["id"]
                for task in state["tasks"]
            },
        )
        self.assertEqual(state["pending_tasks"], 0)

    def test_duplicate_incoming_ids_are_rejected(self):
        engine = self.make_engine()
        engine.start()

        with self.assertRaisesRegex(
            ValueError,
            "must be unique",
        ):
            engine.add_tasks([
                TaskSpec("same", 100),
                TaskSpec("same", 200),
            ])

        self.assertEqual(
            engine.snapshot()["pending_tasks"],
            0,
        )

    def test_pending_tasks_can_be_scheduled(self):
        engine = self.make_engine()
        engine.start()

        incoming = [
            TaskSpec("live-1", 250, arrival_time=0),
            TaskSpec("live-2", 300, arrival_time=0),
        ]

        engine.add_tasks(incoming)
        scheduled = self.schedule(engine, incoming)

        self.assertEqual(scheduled["pending_tasks"], 0)

        runtime_tasks = {
            task["id"]: task
            for task in scheduled["tasks"]
        }

        self.assertIn(
            runtime_tasks["live-1"]["status"],
            {"ASSIGNED", "RUNNING"},
        )
        self.assertIn(
            runtime_tasks["live-2"]["status"],
            {"ASSIGNED", "RUNNING"},
        )

        completed = engine.advance(100)

        self.assertEqual(
            completed["status"],
            "COMPLETED",
        )
        self.assertEqual(
            completed["completed_tasks"],
            3,
        )

    def test_partial_batch_leaves_remaining_tasks_pending(self):
        engine = self.make_engine()
        engine.start()

        incoming = [
            TaskSpec("live-1", 100),
            TaskSpec("live-2", 200),
            TaskSpec("live-3", 300),
        ]

        engine.add_tasks(incoming)
        state = self.schedule(
            engine,
            incoming[:2],
        )

        self.assertEqual(state["pending_tasks"], 1)
        self.assertEqual(
            state["pending_task_ids"],
            ["live-3"],
        )
        self.assertEqual(
            state["pending_work_mi"],
            300,
        )

    def test_non_pending_task_cannot_be_rescheduled(self):
        engine = self.make_engine()
        engine.start()

        invalid_problem = SchedulingProblem(
            [
                TaskSpec("initial", 100),
            ],
            [
                VMSpec("vm-a", 100),
                VMSpec("vm-b", 200),
            ],
        )

        invalid_result = LPTAlgorithm(
            invalid_problem
        ).optimize()

        with self.assertRaisesRegex(
            ValueError,
            "pending task IDs",
        ):
            engine.schedule_pending(
                invalid_result
            )

    def test_completed_simulation_rejects_new_tasks(self):
        engine = self.make_engine()
        engine.start()
        engine.advance(100)

        with self.assertRaisesRegex(
            ValueError,
            "created, running, or paused",
        ):
            engine.add_tasks([
                TaskSpec("too-late", 100),
            ])

    def test_invalid_pending_limit_is_rejected(self):
        engine = self.make_engine()
        engine.start()

        engine.add_tasks([
            TaskSpec("live-1", 100),
        ])

        for invalid in (0, -1, True, 1.5):
            with self.subTest(limit=invalid):
                with self.assertRaises(ValueError):
                    engine.pending_task_specs(
                        invalid
                    )


if __name__ == "__main__":
    unittest.main()