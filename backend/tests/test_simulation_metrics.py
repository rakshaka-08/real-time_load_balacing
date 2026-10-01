import unittest

from app.algorithms.base_algorithm import (
    AlgorithmResult,
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.simulation.metrics import calculate_metrics
from app.simulation.simulation_engine import (
    SimulationEngine,
)


class SimulationMetricsTests(unittest.TestCase):
    def sample_snapshot(self):
        return {
            "simulated_time": 10.0,
            "scheduler_execution_seconds": 0.012,
            "redistribution_count": 2,
            "tasks": [
                {
                    "id": "completed-1",
                    "status": "COMPLETED",
                    "arrival_time": 0.0,
                    "completed_at": 5.0,
                    "remaining_work_mi": 0.0,
                },
                {
                    "id": "completed-2",
                    "status": "COMPLETED",
                    "arrival_time": 2.0,
                    "completed_at": 8.0,
                    "remaining_work_mi": 0.0,
                },
                {
                    "id": "pending",
                    "status": "PENDING",
                    "arrival_time": 4.0,
                    "completed_at": None,
                    "remaining_work_mi": 30.0,
                },
                {
                    "id": "waiting",
                    "status": "WAITING",
                    "arrival_time": 5.0,
                    "completed_at": None,
                    "remaining_work_mi": 20.0,
                },
                {
                    "id": "running",
                    "status": "RUNNING",
                    "arrival_time": 5.0,
                    "completed_at": None,
                    "remaining_work_mi": 10.0,
                },
            ],
            "vms": [
                {
                    "id": "vm-1",
                    "busy_seconds": 4.0,
                },
                {
                    "id": "vm-2",
                    "busy_seconds": 6.0,
                },
            ],
        }

    def test_calculates_actual_simulation_metrics(self):
        metrics = calculate_metrics(
            self.sample_snapshot()
        )

        self.assertEqual(
            metrics["system_utilization"],
            50.0,
        )
        self.assertEqual(
            metrics["total_response_time"],
            11.0,
        )
        self.assertEqual(
            metrics["average_response_time"],
            5.5,
        )
        self.assertEqual(
            metrics["makespan"],
            8.0,
        )
        self.assertEqual(
            metrics["load_imbalance"],
            0.2,
        )
        self.assertEqual(
            metrics["scheduler_execution_seconds"],
            0.012,
        )
        self.assertEqual(
            metrics["redistribution_count"],
            2,
        )

    def test_backlog_counts_only_waiting_work(self):
        metrics = calculate_metrics(
            self.sample_snapshot()
        )

        self.assertEqual(
            metrics["backlog_tasks"],
            2,
        )
        self.assertEqual(
            metrics["backlog_work_mi"],
            50.0,
        )

    def test_running_tasks_are_not_backlog(self):
        snapshot = self.sample_snapshot()
        snapshot["tasks"] = [
            {
                "status": "RUNNING",
                "remaining_work_mi": 100.0,
            }
        ]

        metrics = calculate_metrics(snapshot)

        self.assertEqual(
            metrics["backlog_tasks"],
            0,
        )
        self.assertEqual(
            metrics["backlog_work_mi"],
            0.0,
        )

    def test_empty_snapshot_returns_zero_metrics(self):
        metrics = calculate_metrics({
            "simulated_time": 0.0,
            "tasks": [],
            "vms": [],
        })

        self.assertEqual(
            metrics["system_utilization"],
            0.0,
        )
        self.assertEqual(
            metrics["average_response_time"],
            0.0,
        )
        self.assertEqual(
            metrics["load_imbalance"],
            0.0,
        )
        self.assertEqual(
            metrics["makespan"],
            0.0,
        )

    def test_invalid_snapshot_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "snapshot must be a dictionary",
        ):
            calculate_metrics(None)

    def test_engine_snapshot_contains_metrics(self):
        problem = SchedulingProblem(
            [TaskSpec("task", 100.0)],
            [VMSpec("vm", 100.0)],
        )
        schedule = problem.evaluate(("task",))
        result = AlgorithmResult(
            algorithm="TEST",
            schedule=schedule,
            execution_seconds=0.25,
            iterations=1,
            seed=42,
        )

        engine = SimulationEngine(
            problem,
            result,
            {"vm": 10.0},
        )

        engine.start()
        snapshot = engine.advance(1.0)

        self.assertEqual(
            snapshot["metrics"][
                "system_utilization"
            ],
            100.0,
        )
        self.assertEqual(
            snapshot["metrics"][
                "total_response_time"
            ],
            1.0,
        )
        self.assertEqual(
            snapshot["metrics"]["makespan"],
            1.0,
        )

    def test_scheduler_time_accumulates_for_batches(self):
        problem = SchedulingProblem(
            [TaskSpec("initial", 100.0)],
            [VMSpec("vm", 100.0)],
        )
        initial_schedule = problem.evaluate(
            ("initial",)
        )
        initial_result = AlgorithmResult(
            algorithm="TEST",
            schedule=initial_schedule,
            execution_seconds=0.25,
            iterations=1,
            seed=42,
        )

        engine = SimulationEngine(
            problem,
            initial_result,
            {"vm": 10.0},
        )

        engine.set_workload_open(True)
        engine.start()
        engine.add_tasks([
            TaskSpec("injected", 50.0),
        ])

        batch_problem = SchedulingProblem(
            engine.pending_task_specs(),
            engine.vm_specs(),
        )
        batch_schedule = batch_problem.evaluate(
            ("injected",)
        )
        batch_result = AlgorithmResult(
            algorithm="TEST",
            schedule=batch_schedule,
            execution_seconds=0.5,
            iterations=1,
            seed=42,
        )

        snapshot = engine.schedule_pending(
            batch_result
        )

        self.assertEqual(
            snapshot[
                "scheduler_execution_seconds"
            ],
            0.75,
        )
        self.assertEqual(
            snapshot["metrics"][
                "scheduler_execution_seconds"
            ],
            0.75,
        )


if __name__ == "__main__":
    unittest.main()