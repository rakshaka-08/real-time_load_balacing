import unittest

from time import time
from unittest.mock import patch

from app.sockets.realtime_payload import (
    build_realtime_payload,
)
from app.sockets.simulation_socket import (
    SimulationNamespace,
)


class RealtimeMetricsSocketTests(
    unittest.TestCase
):
    def sample_state(self):
        return {
            "id": "simulation-1",
            "revision": 7,
            "status": "RUNNING",
            "simulated_time": 8.5,
            "pending_tasks": 4,
            "running_tasks": 2,
            "completed_tasks": 10,
            "total_tasks": 16,
            "tasks": [],
            "vms": [],
            "metrics": {
                "system_utilization": 73.25,
                "total_response_time": 41.8,
                "average_response_time": 4.18,
                "makespan": 8.1,
                "load_imbalance": 0.16,
                "backlog_tasks": 4,
                "backlog_work_mi": 850.0,
                "scheduler_execution_seconds": (
                    0.021
                ),
                "redistribution_count": 3,
            },
        }

    def test_builds_realtime_metric_summary(self):
        payload = build_realtime_payload(
            self.sample_state()
        )
        metrics = payload[
            "realtime_metrics"
        ]

        self.assertEqual(
            metrics["simulation_id"],
            "simulation-1",
        )
        self.assertEqual(
            metrics["system_utilization"],
            73.25,
        )
        self.assertEqual(
            metrics["backlog_tasks"],
            4,
        )
        self.assertEqual(
            metrics["redistribution_count"],
            3,
        )

    def test_preserves_complete_simulation_state(self):
        state = self.sample_state()
        payload = build_realtime_payload(state)

        self.assertEqual(
            payload["tasks"],
            state["tasks"],
        )
        self.assertEqual(
            payload["vms"],
            state["vms"],
        )
        self.assertEqual(
            payload["metrics"],
            state["metrics"],
        )

    def test_does_not_mutate_original_state(self):
        state = self.sample_state()

        build_realtime_payload(state)

        self.assertNotIn(
            "realtime_metrics",
            state,
        )

    def test_legacy_state_remains_compatible(self):
        state = {
            "id": "old-simulation",
            "revision": 1,
            "status": "COMPLETED",
        }

        payload = build_realtime_payload(state)

        self.assertEqual(payload, state)
        self.assertNotIn(
            "realtime_metrics",
            payload,
        )

    def test_invalid_state_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "simulation state must be a dictionary",
        ):
            build_realtime_payload(None)

    def test_namespace_uses_existing_event(self):
        namespace = SimulationNamespace()

        namespace._clients["socket-1"] = {
            "owner_id": "owner-1",
            "expires_at": time() + 60,
            "simulation_id": "simulation-1",
            "last_revision": -1,
        }

        state = self.sample_state()

        with patch.object(
            namespace,
            "emit",
        ) as emit:
            namespace._send_state(
                "socket-1",
                state,
            )

        emit.assert_called_once()

        event_name, payload = (
            emit.call_args.args
        )

        self.assertEqual(
            event_name,
            "simulation_state",
        )
        self.assertIn(
            "realtime_metrics",
            payload,
        )
        self.assertEqual(
            emit.call_args.kwargs["room"],
            "socket-1",
        )
        self.assertEqual(
            namespace._clients[
                "socket-1"
            ]["last_revision"],
            7,
        )


if __name__ == "__main__":
    unittest.main()