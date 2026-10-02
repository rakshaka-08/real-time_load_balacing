# Module 26 — Configurable micro-batch scheduling

## Purpose

The micro-batch scheduler combines tasks from the runtime pending queue and
passes them to an existing scheduling algorithm. Batches are dispatched when
the configured size or time interval is reached.

## Configuration

- `batch_size`: maximum number of tasks in one batch
- `batch_interval`: maximum simulated seconds before a partial batch runs
- `seed`: starting seed for deterministic batch scheduling
- `algorithm_class`: existing scheduling algorithm class
- `algorithm_parameters`: existing algorithm configuration

## Flow

```text
TaskGenerator
→ SimulationEngine pending queue
→ Batch size or interval trigger
→ Existing algorithm
→ AlgorithmResult
→ SimulationEngine.schedule_pending()
→ Existing VM queues
→ Existing redistribution
→ Existing task execution
```

## Validation

- Full batches dispatch when `batch_size` is reached.
- Partial batches dispatch when `batch_interval` expires.
- Scheduling seeds remain deterministic across batches.
- Existing VM execution and redistribution behavior is preserved.
