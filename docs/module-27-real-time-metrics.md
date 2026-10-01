# Module 27 — Real-time simulation metrics

## Purpose

This module calculates performance metrics from the existing simulation
snapshot. It does not replace the simulation engine, algorithms, API,
authentication, database, or Socket.IO implementation.

## Metrics

- **System utilization:** total VM busy time divided by total available
  VM time, expressed as a percentage.
- **Total response time:** sum of completion time minus arrival time for
  every completed task.
- **Average response time:** total response time divided by completed
  task count.
- **Makespan:** latest actual task completion time.
- **Load imbalance:** population standard deviation of VM utilization
  divided by mean VM utilization.
- **Backlog tasks:** tasks in PENDING, WAITING, or ASSIGNED state.
- **Backlog workload:** remaining MI for backlog tasks.
- **Scheduler execution time:** accumulated execution time for the
  initial schedule and later micro-batches.
- **Redistribution count:** actual migrations recorded by the existing
  load balancer.

## Integration

Metrics are stored in the `metrics` property of every simulation
snapshot. The existing Socket.IO publisher already transports the
snapshot, so no second real-time channel is introduced.