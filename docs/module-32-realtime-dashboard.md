# Module 32 — Real-time dashboard visualization

The simulation dashboard now visualizes actual Socket.IO state:

- Active virtual machines
- Tasks arriving in the latest simulated second
- Waiting, running, completed, and failed task flow
- Backlog tasks and workload
- System utilization
- Load imbalance
- Per-VM utilization and queue length
- Recorded redistribution activity

No values are hardcoded. Missing redistribution reasons are not
invented. Existing simulation controls, REST refresh, JWT
authentication, and Socket.IO subscription behavior remain unchanged.