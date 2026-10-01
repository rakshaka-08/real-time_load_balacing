import unittest

from app.algorithms.base_algorithm import (
    SchedulingProblem,
    TaskSpec,
    VMSpec,
)
from app.algorithms.lpt import LPTAlgorithm
from app.simulation.micro_batcher import (
    MicroBatchConfig,
    MicroBatchScheduler,
)
from app.simulation.simulation_engine import (
    SimulationEngine,
)
from app.simulation.task_generator import (
    TaskGenerator,
    TaskGeneratorConfig,
)


class MicroBatchSchedulerTests(unittest.TestCase):
    def make_scheduler(
        self,
        *,
        batch_size=2,
        batch_interval=1.0,
        arrival_rate=100.0,
        max_tasks=4,
        start_time=0.0,
        generator_seed=42,
        scheduler_seed=100,
    ):
        vm_specs = [
            VMSpec("vm-a", 100),
            VMSpec("vm-b", 200),
        ]

        problem = SchedulingProblem(
            [],
            vm_specs,
        )
        initial_result = LPTAlgorithm(
            problem
        ).optimize()

        engine = SimulationEngine(
            problem,
            initial_result,
            {
                "vm-a": 10,
                "vm-b": 10,
            },
        )

        generator = TaskGenerator(
            TaskGeneratorConfig(
                arrival_rate=arrival_rate,
                min_work_mi=100,
                max_work_mi=300,
                seed=generator_seed,
                max_tasks=max_tasks,
                start_time=start_time,
                task_id_prefix="live",
            )
        )

        scheduler = MicroBatchScheduler(
            engine=engine,
            generator=generator,
            algorithm_class=LPTAlgorithm,
            config=MicroBatchConfig(
                batch_size=batch_size,
                batch_interval=batch_interval,
                seed=scheduler_seed,
            ),
        )

        return engine, generator, scheduler

    def test_open_workload_keeps_empty_engine_running(self):
        engine, _, _ = self.make_scheduler(
            start_time=10,
        )

        state = engine.start()

        self.assertEqual(
            state["status"],
            "RUNNING",
        )
        self.assertTrue(
            state["workload_open"],
        )
        self.assertEqual(
            state["total_tasks"],
            0,
        )

    def test_batch_size_triggers_scheduling(self):
        engine, generator, scheduler = (
            self.make_scheduler(
                batch_size=2,
                batch_interval=100,
                max_tasks=2,
            )
        )

        engine.start()

        scheduler.advance(
            generator.next_arrival_time
        )

        self.assertEqual(
            engine.snapshot()["pending_tasks"],
            1,
        )

        second_arrival = (
            generator.next_arrival_time
        )

        scheduler.advance(
            second_arrival
            - engine.snapshot()["simulated_time"]
        )

        scheduler_state = scheduler.snapshot()
        simulation = engine.snapshot()

        self.assertEqual(
            scheduler_state["batch_count"],
            1,
        )
        self.assertEqual(
            scheduler_state["scheduled_task_count"],
            2,
        )
        self.assertEqual(
            simulation["pending_tasks"],
            0,
        )

    def test_interval_schedules_partial_batch(self):
        engine, generator, scheduler = (
            self.make_scheduler(
                batch_size=10,
                batch_interval=1,
                max_tasks=1,
            )
        )

        engine.start()

        scheduler.advance(
            generator.next_arrival_time
        )

        self.assertEqual(
            engine.snapshot()["pending_tasks"],
            1,
        )

        scheduler.advance(
            1
            - engine.snapshot()["simulated_time"]
        )

        self.assertEqual(
            scheduler.snapshot()["batch_count"],
            1,
        )
        self.assertEqual(
            engine.snapshot()["pending_tasks"],
            0,
        )

    def test_existing_algorithm_schedules_manual_batch(self):
        engine, _, scheduler = (
            self.make_scheduler(
                batch_size=2,
                batch_interval=100,
                max_tasks=1,
                start_time=1000,
            )
        )

        engine.start()

        engine.add_tasks([
            TaskSpec("manual-a", 500),
            TaskSpec("manual-b", 100),
        ])

        scheduler.process_current_time()

        state = engine.snapshot()
        tasks = {
            task["id"]: task
            for task in state["tasks"]
        }

        self.assertEqual(
            state["pending_tasks"],
            0,
        )
        self.assertIn(
            tasks["manual-a"]["status"],
            {"RUNNING", "ASSIGNED"},
        )
        self.assertIn(
            tasks["manual-b"]["status"],
            {"RUNNING", "ASSIGNED"},
        )
        self.assertEqual(
            scheduler.snapshot()["batch_count"],
            1,
        )

    def test_scheduler_records_real_execution_time(self):
        engine, generator, scheduler = (
            self.make_scheduler(
                batch_size=1,
                max_tasks=1,
            )
        )

        engine.start()
        scheduler.advance(
            generator.next_arrival_time
        )

        state = scheduler.snapshot()

        self.assertEqual(
            state["batch_count"],
            1,
        )
        self.assertGreaterEqual(
            state["scheduler_execution_seconds"],
            0,
        )
        self.assertEqual(
            len(state["batches"]),
            1,
        )
        self.assertEqual(
            state["batches"][0]["algorithm"],
            "LPT",
        )

    def test_identical_configuration_is_deterministic(self):
        first_engine, _, first = (
            self.make_scheduler()
        )
        second_engine, _, second = (
            self.make_scheduler()
        )

        first_engine.start()
        second_engine.start()

        first.advance(5)
        second.advance(5)

        first_tasks = [
            (
                task["id"],
                task["work_mi"],
                task["arrival_time"],
                task["vm_id"],
                task["status"],
            )
            for task in first_engine.snapshot()["tasks"]
        ]

        second_tasks = [
            (
                task["id"],
                task["work_mi"],
                task["arrival_time"],
                task["vm_id"],
                task["status"],
            )
            for task in second_engine.snapshot()["tasks"]
        ]

        self.assertEqual(
            first_tasks,
            second_tasks,
        )

    def test_invalid_configuration_is_rejected(self):
        invalid_values = [
            {
                "batch_size": 0,
            },
            {
                "batch_size": 501,
            },
            {
                "batch_size": True,
            },
            {
                "batch_interval": 0,
            },
            {
                "batch_interval": -1,
            },
            {
                "seed": True,
            },
            {
                "seed": 2**32,
            },
        ]

        for changes in invalid_values:
            values = {
                "batch_size": 5,
                "batch_interval": 1,
                "seed": 42,
            }
            values.update(changes)

            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    MicroBatchConfig(**values)

    def test_advance_requires_running_simulation(self):
        _, _, scheduler = self.make_scheduler()

        with self.assertRaisesRegex(
            ValueError,
            "Start the simulation",
        ):
            scheduler.advance(1)


if __name__ == "__main__":
    unittest.main()