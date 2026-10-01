# Module 25 — Runtime task injection and pending queue

## Purpose

The existing SimulationEngine can now accept TaskSpec objects while it is
created, running, or paused. New tasks remain pending until a scheduling
algorithm assigns them to virtual machines.

## Runtime flow

```text
Generated TaskSpec
→ SimulationEngine.add_tasks()
→ Pending queue
→ AlgorithmResult
→ SimulationEngine.schedule_pending()
→ Existing VM queues
→ Existing redistribution
→ Existing task execution