# Module 24 — Continuous real-time task generator

## Purpose

The task generator creates deterministic task arrivals as simulated time
advances. It is part of the existing simulation package and produces the
existing `TaskSpec` objects.

## Configuration

- `arrival_rate`: expected tasks per simulated second
- `min_work_mi`: minimum generated task work
- `max_work_mi`: maximum generated task work
- `seed`: deterministic random seed
- `max_tasks`: generation safety limit
- `start_time`: simulated time from which arrivals begin
- `task_id_prefix`: prefix used for unique generated task IDs

## Arrival model

Inter-arrival durations use an exponential distribution. Calling
`generate_until(time)` returns every task whose generated arrival time is
less than or equal to that simulated time.

Calling the generator incrementally produces the same workload as advancing
directly to the final time when the configuration and seed are identical.

## Architecture

This module reuses `TaskSpec` and does not change:

- REST APIs
- JWT authentication
- MongoDB collections
- scheduling algorithms
- SimulationEngine
- Socket.IO events

SimulationEngine integration and micro-batching are implemented in later
modules.