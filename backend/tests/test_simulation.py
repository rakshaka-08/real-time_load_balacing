import unittest

from app.algorithms.base_algorithm import (
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.algorithms.lpt import LPTAlgorithm
from app.simulation.simulation_engine import SimulationEngine
from unittest.mock import patch
from app.simulation.load_balancer import rebalance_queues
from app.simulation.task_executor import TaskRuntime
from app.simulation.vm_scheduler import VMRuntime

class SimulationEngineTests(unittest.TestCase):
    def make_engine(self, tasks=None, threshold=10):
        if tasks is None:
            tasks = [
                TaskSpec("a", 200),
                TaskSpec("b", 100),
            ]

        problem = SchedulingProblem(
            tasks,
            [VMSpec("vm", 100)],
        )
        result = LPTAlgorithm(problem).optimize()

        return SimulationEngine(
            problem,
            result,
            {"vm": threshold},
        )

    def test_start_assigns_and_dispatches_tasks(self):
        engine = self.make_engine()

        self.assertEqual(engine.snapshot()["status"], "CREATED")

        state = engine.start()
        tasks = {task["id"]: task for task in state["tasks"]}

        self.assertEqual(state["status"], "RUNNING")
        self.assertEqual(tasks["a"]["status"], "RUNNING")
        self.assertEqual(tasks["b"]["status"], "ASSIGNED")
        self.assertEqual(state["vms"][0]["queued_task_ids"], ["b"])

    def test_execution_records_actual_completion_times(self):
        engine = self.make_engine()
        engine.start()

        partial = engine.advance(0.5)
        self.assertAlmostEqual(
            partial["tasks"][0]["remaining_work_mi"], 150
        )

        final = engine.advance(100)
        tasks = {task["id"]: task for task in final["tasks"]}

        self.assertEqual(final["status"], "COMPLETED")
        self.assertEqual(final["simulated_time"], 3)
        self.assertEqual(tasks["a"]["completed_at"], 2)
        self.assertEqual(tasks["b"]["started_at"], 2)
        self.assertEqual(tasks["b"]["completed_at"], 3)
        self.assertEqual(final["vms"][0]["busy_seconds"], 3)
        self.assertEqual(final["completed_tasks"], 2)

    def test_pause_freezes_time_and_resume_continues(self):
        engine = self.make_engine()
        engine.start()
        engine.advance(0.5)

        paused = engine.pause()
        after_wait = engine.advance(100)

        self.assertEqual(after_wait, paused)

        engine.resume()
        final = engine.advance(2.5)

        self.assertEqual(final["status"], "COMPLETED")
        self.assertEqual(final["simulated_time"], 3)

    def test_stop_preserves_partial_run(self):
        engine = self.make_engine()
        engine.start()
        engine.advance(0.5)

        stopped = engine.stop()

        self.assertEqual(stopped["status"], "STOPPED")
        self.assertEqual(stopped["completed_tasks"], 0)
        self.assertEqual(engine.advance(100), stopped)

        with self.assertRaises(ValueError):
            engine.resume()

    def test_future_arrivals_do_not_execute_early(self):
        engine = self.make_engine(
            tasks=[TaskSpec("later", 200, arrival_time=10)]
        )
        engine.start()

        waiting = engine.advance(5)

        self.assertEqual(waiting["simulated_time"], 5)
        self.assertEqual(waiting["tasks"][0]["status"], "WAITING")
        self.assertEqual(waiting["vms"][0]["busy_seconds"], 0)

        final = engine.advance(100)

        self.assertEqual(final["tasks"][0]["started_at"], 10)
        self.assertEqual(final["tasks"][0]["completed_at"], 12)
        self.assertEqual(final["simulated_time"], 12)

    def test_reset_creates_fresh_run_without_erasing_old_run(self):
        engine = self.make_engine()
        engine.start()
        old_state = engine.advance(100)

        fresh = engine.reset()

        self.assertIsNot(fresh, engine)
        self.assertEqual(engine.snapshot(), old_state)
        self.assertEqual(fresh.snapshot()["status"], "CREATED")
        self.assertEqual(fresh.snapshot()["simulated_time"], 0)

        fresh.start()
        self.assertEqual(fresh.advance(100), old_state)

    def test_overload_detection_uses_queued_seconds(self):
        engine = self.make_engine(threshold=0.5)
        state = engine.start()

        self.assertEqual(state["vms"][0]["queued_seconds"], 1)
        self.assertEqual(state["vms"][0]["status"], "OVERLOADED")

        state = engine.advance(2)

        self.assertEqual(state["vms"][0]["queued_seconds"], 0)
        self.assertEqual(state["vms"][0]["status"], "RUNNING")

    def test_empty_workload_finishes_immediately(self):
        engine = self.make_engine(tasks=[])
        state = engine.start()

        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["simulated_time"], 0)
        self.assertEqual(state["total_tasks"], 0)

    def test_invalid_controls_and_time_are_rejected(self):
        engine = self.make_engine()

        with self.assertRaises(ValueError):
            engine.advance(1)

        with self.assertRaises(ValueError):
            engine.pause()

        with self.assertRaises(ValueError):
            engine.reset()

        engine.start()

        with self.assertRaises(ValueError):
            engine.start()

        for seconds in (-1, True, float("inf"), float("nan")):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):
                    engine.advance(seconds)

        self.assertEqual(engine.snapshot()["status"], "RUNNING")

class LoadBalancerTests(unittest.TestCase):
    def make_imbalanced_state(self):
        tasks = {
            "running": TaskRuntime(
                spec=TaskSpec("running", 500),
                vm_id="source",
                status="ASSIGNED",
                assigned_at=0,
            ),
            "queued": TaskRuntime(
                spec=TaskSpec("queued", 200),
                vm_id="source",
                status="ASSIGNED",
                assigned_at=0,
            ),
        }

        source = VMRuntime(
            spec=VMSpec("source", 100),
            overload_threshold=0.5,
        )
        destination = VMRuntime(
            spec=VMSpec("destination", 200),
            overload_threshold=2,
        )

        source.queue.extend(["running", "queued"])
        source.dispatch(tasks, 0)

        return tasks, {
            "source": source,
            "destination": destination,
        }

    def test_moves_queued_task_to_faster_available_vm(self):
        tasks, vms = self.make_imbalanced_state()

        migrations = rebalance_queues(vms, tasks, now=0)

        self.assertEqual(len(migrations), 1)
        self.assertEqual(migrations[0]["task_id"], "queued")
        self.assertEqual(tasks["queued"].vm_id, "destination")
        self.assertEqual(list(vms["source"].queue), [])
        self.assertEqual(
            list(vms["destination"].queue),
            ["queued"],
        )

        vms["destination"].dispatch(tasks, 0)

        self.assertEqual(tasks["queued"].status, "RUNNING")
        self.assertEqual(tasks["queued"].expected_finish, 1)

    def test_running_task_is_not_moved(self):
        tasks, vms = self.make_imbalanced_state()

        rebalance_queues(vms, tasks, now=0)

        self.assertEqual(tasks["running"].vm_id, "source")
        self.assertEqual(tasks["running"].started_at, 0)
        self.assertEqual(tasks["running"].expected_finish, 5)
        self.assertEqual(
            vms["source"].current_task_id,
            "running",
        )

    def test_destination_threshold_is_respected(self):
        tasks, vms = self.make_imbalanced_state()
        vms["destination"].overload_threshold = 0.5

        migrations = rebalance_queues(vms, tasks, now=0)

        self.assertEqual(migrations, [])
        self.assertEqual(tasks["queued"].vm_id, "source")

    def test_slower_completion_is_rejected(self):
        tasks, vms = self.make_imbalanced_state()
        vms["destination"].spec = VMSpec("destination", 10)
        vms["destination"].overload_threshold = 100

        migrations = rebalance_queues(vms, tasks, now=0)

        self.assertEqual(migrations, [])
        self.assertEqual(tasks["queued"].vm_id, "source")

    def test_repeated_balancing_does_not_duplicate_tasks(self):
        tasks, vms = self.make_imbalanced_state()

        rebalance_queues(vms, tasks, now=0)
        second_pass = rebalance_queues(vms, tasks, now=0)

        self.assertEqual(second_pass, [])

        queued_ids = [
            task_id
            for vm in vms.values()
            for task_id in vm.queue
        ]

        self.assertEqual(queued_ids, ["queued"])
        self.assertEqual(tasks["queued"].status, "ASSIGNED")

    def test_engine_can_disable_redistribution_and_preserves_setting(self):
        problem = SchedulingProblem(
            [TaskSpec("task", 100)],
            [VMSpec("vm", 100)],
        )
        result = LPTAlgorithm(problem).optimize()

        engine = SimulationEngine(
            problem,
            result,
            {"vm": 10},
            enable_redistribution=False,
        )

        with patch(
            "app.simulation.simulation_engine.rebalance_queues"
        ) as balance:
            engine.start()
            final = engine.advance(10)

        balance.assert_not_called()
        self.assertEqual(final["status"], "COMPLETED")
        self.assertEqual(final["redistribution_count"], 0)

        fresh = engine.reset()
        self.assertFalse(fresh.snapshot()["redistribution_enabled"])

    def test_engine_invokes_balancer_when_enabled(self):
        problem = SchedulingProblem(
            [TaskSpec("task", 100)],
            [VMSpec("vm", 100)],
        )
        result = LPTAlgorithm(problem).optimize()

        engine = SimulationEngine(
            problem,
            result,
            {"vm": 10},
        )

        with patch(
            "app.simulation.simulation_engine.rebalance_queues",
            return_value=[],
        ) as balance:
            engine.start()
            balance.assert_called_once()
            self.assertEqual(balance.call_args.args[2], 0.0)

            balance.reset_mock()
            final = engine.advance(1)
            balance.assert_called_once()
            self.assertEqual(balance.call_args.args[2], 1.0)

        self.assertEqual(final["status"], "COMPLETED")
        self.assertTrue(final["redistribution_enabled"]) 

if __name__ == "__main__":
    unittest.main()