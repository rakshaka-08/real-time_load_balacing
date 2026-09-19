import math


def remaining_running_seconds(vm, tasks, now):
    if vm.current_task_id is None:
        return 0.0

    task = tasks[vm.current_task_id]
    return max(0.0, task.expected_finish - now)


def rebalance_queues(vms, tasks, now):
    migrations = []
    moved_tasks = set()

    for source_id in sorted(vms):
        source = vms[source_id]

        while (
            source.queue
            and source.queued_seconds(tasks) > source.overload_threshold
        ):
            # Moving the tail does not delay other tasks in the source queue.
            task_id = source.queue[-1]
            task = tasks[task_id]

            if task.status != "ASSIGNED":
                raise RuntimeError(
                    "Only assigned, unstarted tasks may be queued."
                )

            if task_id in moved_tasks:
                break

            source_finish = (
                now
                + remaining_running_seconds(source, tasks, now)
                + source.queued_seconds(tasks)
            )

            candidates = []

            for destination_id in sorted(vms):
                if destination_id == source_id:
                    continue

                destination = vms[destination_id]
                duration = (
                    task.spec.work_mi / destination.spec.capacity_mips
                )
                projected_queue = (
                    destination.queued_seconds(tasks) + duration
                )
                destination_finish = (
                    now
                    + remaining_running_seconds(destination, tasks, now)
                    + projected_queue
                )

                if not math.isfinite(destination_finish):
                    continue

                if projected_queue > destination.overload_threshold:
                    continue

                if destination_finish >= source_finish:
                    continue

                candidates.append(
                    (destination_finish, destination_id)
                )

            if not candidates:
                break

            _, destination_id = min(candidates)
            destination = vms[destination_id]

            source.queue.pop()
            destination.queue.append(task_id)
            task.vm_id = destination_id
            moved_tasks.add(task_id)

            migrations.append({
                "time": now,
                "task_id": task_id,
                "from_vm_id": source_id,
                "to_vm_id": destination_id,
            })

    return migrations