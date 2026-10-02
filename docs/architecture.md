# System architecture

## Frontend

The React application handles authentication, task and VM management, simulation configuration, live monitoring, analytics, reporting, replay, templates, and health status. Axios sends JWT-authenticated REST requests. The Socket.IO client receives private simulation snapshots and reconnects to the selected run.

## Backend

Flask blueprints expose authentication, task, VM, simulation, template, and health endpoints. Service modules validate requests, enforce ownership, and coordinate persistence. Socket handlers authenticate connections and restrict subscriptions to simulations owned by the connected user.

## Simulation pipeline

```text
Selected or generated tasks
        ↓
Runtime pending queue
        ↓
Micro-batch scheduler
        ↓
GA / HBA / Hybrid GA + HBA / LPT / SPT
        ↓
Per-VM execution queues
        ↓
Optional overload redistribution
        ↓
Metrics, persisted snapshots, and Socket.IO updates
```

## Persistence

MongoDB stores users, tasks, virtual machines, simulations, and scenario templates. Records use owner identifiers so API and socket access can enforce isolation between accounts.

## Operational boundaries

- JWT access tokens expire after one hour.
- The development server uses one local process.
- Background simulation runners are recovered from persisted active runs at startup.
- Visual rack groups do not influence scheduling decisions.
- Benchmark comparisons reuse the same workload, VM configuration, seed, and redistribution setting for every algorithm.
