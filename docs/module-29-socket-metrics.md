# Module 29 — Socket.IO real-time metrics delivery

## Existing event

The application continues to use:

`simulation_state`

No additional WebSocket server or unauthenticated event was created.

## Payload

The complete simulation state remains available. New simulations also
include a `realtime_metrics` summary containing:

- Simulation status and simulated time
- Pending, running, completed, and total task counts
- System utilization
- Total and average response time
- Makespan
- Load imbalance
- Backlog task count and workload
- Accumulated scheduler execution time
- Redistribution count

All values come from the simulation engine and centralized metrics
module.

## Security

Existing JWT authentication, simulation ownership validation, private
socket delivery, token-expiration checks, revision ordering, and
reconnection behavior remain active.

Legacy simulations without metrics continue using their original
payload.