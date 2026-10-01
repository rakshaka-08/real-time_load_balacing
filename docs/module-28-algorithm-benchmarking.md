# Module 28 — Fair algorithm benchmarking

## Purpose

This module compares GA, HBA, GA-HBA, LPT, and SPT under identical
simulation conditions.

## Fairness controls

Every algorithm receives:

- The same task specifications
- The same task arrival times
- The same VM specifications
- The same VM capacities
- The same overload thresholds
- The same random seed
- The same redistribution setting

## Execution

Each algorithm uses its existing implementation and produces an
`AlgorithmResult`. That result is executed through the existing
`SimulationEngine`.

The comparison therefore uses actual runtime metrics rather than
hardcoded or estimated graph values.

## Returned metrics

- System utilization
- Total response time
- Average response time
- Makespan
- Load imbalance
- Scheduler execution time
- Redistribution count

## Endpoint

`POST /api/simulations/benchmark`

The endpoint is protected by the existing JWT authentication and loads
only tasks and VMs owned by the authenticated user.