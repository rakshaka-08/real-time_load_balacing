import unittest

from app.simulation.task_generator import (
    MAX_GENERATED_TASKS,
    TaskGenerator,
    TaskGeneratorConfig,
)


class TaskGeneratorTests(unittest.TestCase):
    def make_config(self, **changes):
        values = {
            "arrival_rate": 2.0,
            "min_work_mi": 100.0,
            "max_work_mi": 500.0,
            "seed": 42,
            "max_tasks": 100,
            "start_time": 0.0,
            "task_id_prefix": "incoming",
        }
        values.update(changes)

        return TaskGeneratorConfig(**values)

    def test_same_seed_produces_same_tasks(self):
        first = TaskGenerator(self.make_config())
        second = TaskGenerator(self.make_config())

        self.assertEqual(
            first.generate_until(10),
            second.generate_until(10),
        )

    def test_tasks_are_generated_only_after_arrival(self):
        generator = TaskGenerator(self.make_config())
        first_arrival = generator.next_arrival_time

        before = generator.generate_until(
            max(0.0, first_arrival - 0.000001)
        )
        at_arrival = generator.generate_until(first_arrival)

        self.assertEqual(before, ())
        self.assertEqual(len(at_arrival), 1)
        self.assertEqual(
            at_arrival[0].arrival_time,
            first_arrival,
        )

    def test_generated_tasks_have_unique_ids_and_valid_work(self):
        config = self.make_config(
            min_work_mi=250,
            max_work_mi=750,
        )
        generator = TaskGenerator(config)

        tasks = generator.generate_until(20)
        task_ids = [task.id for task in tasks]

        self.assertTrue(tasks)
        self.assertEqual(len(task_ids), len(set(task_ids)))

        for position, task in enumerate(tasks, start=1):
            self.assertEqual(
                task.id,
                f"incoming-{position:06d}",
            )
            self.assertGreaterEqual(task.work_mi, 250)
            self.assertLessEqual(task.work_mi, 750)
            self.assertLessEqual(task.arrival_time, 20)

    def test_incremental_generation_matches_single_advance(self):
        incremental = TaskGenerator(self.make_config())
        combined = (
            incremental.generate_until(2)
            + incremental.generate_until(5)
            + incremental.generate_until(10)
        )

        direct = TaskGenerator(self.make_config())
        all_at_once = direct.generate_until(10)

        self.assertEqual(combined, all_at_once)

    def test_generator_stops_at_maximum_task_count(self):
        generator = TaskGenerator(
            self.make_config(
                arrival_rate=100,
                max_tasks=5,
            )
        )

        tasks = generator.generate_until(100)

        self.assertEqual(len(tasks), 5)
        self.assertEqual(generator.generated_count, 5)
        self.assertTrue(generator.exhausted)
        self.assertIsNone(generator.next_arrival_time)
        self.assertEqual(generator.generate_until(200), ())

    def test_simulated_time_cannot_move_backward(self):
        generator = TaskGenerator(self.make_config())

        generator.generate_until(10)

        with self.assertRaisesRegex(
            ValueError,
            "cannot move backward",
        ):
            generator.generate_until(5)

    def test_snapshot_reports_generator_state(self):
        generator = TaskGenerator(
            self.make_config(max_tasks=3)
        )

        tasks = generator.generate_until(100)
        snapshot = generator.snapshot()

        self.assertEqual(len(tasks), 3)
        self.assertEqual(snapshot["generated_count"], 3)
        self.assertTrue(snapshot["exhausted"])
        self.assertIsNone(snapshot["next_arrival_time"])
        self.assertEqual(
            snapshot["configuration"]["arrival_rate"],
            2.0,
        )

    def test_invalid_configuration_is_rejected(self):
        invalid_configurations = [
            {
                "arrival_rate": 0,
            },
            {
                "min_work_mi": 0,
            },
            {
                "min_work_mi": 500,
                "max_work_mi": 100,
            },
            {
                "seed": True,
            },
            {
                "seed": 2**32,
            },
            {
                "max_tasks": 0,
            },
            {
                "max_tasks": MAX_GENERATED_TASKS + 1,
            },
            {
                "start_time": -1,
            },
            {
                "task_id_prefix": "",
            },
            {
                "task_id_prefix": "x" * 41,
            },
        ]

        for changes in invalid_configurations:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.make_config(**changes)

    def test_non_configuration_object_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "TaskGeneratorConfig",
        ):
            TaskGenerator({})
            

if __name__ == "__main__":
    unittest.main()