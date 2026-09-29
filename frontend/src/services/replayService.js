export function formatReplayTime(value) {
    return Number(value || 0).toLocaleString(undefined, {
      maximumFractionDigits: 2,
    });
  }
  
  export function getReplayEndTime(simulation) {
    const taskTimes = (simulation.tasks || []).flatMap((task) => [
      Number(task.started_at || 0),
      Number(task.completed_at || 0),
    ]);
  
    return Math.max(
      Number(simulation.simulated_time || 0),
      ...taskTimes,
      0
    );
  }
  
  function taskStatusAt(task, time) {
    const startedAt = Number(task.started_at);
    const completedAt = Number(task.completed_at);
  
    if (!Number.isFinite(startedAt) || time < startedAt) {
      return "WAITING";
    }
  
    if (!Number.isFinite(completedAt) || time < completedAt) {
      return "RUNNING";
    }
  
    return "COMPLETED";
  }
  
  export function buildReplayState(simulation, time) {
    const tasks = (simulation.tasks || []).map((task) => ({
      ...task,
      replay_status: taskStatusAt(task, time),
    }));
  
    const vms = (simulation.vms || []).map((vm) => {
      const assigned = tasks.filter((task) => task.vm_id === vm.id);
      const active = assigned.find((task) => task.replay_status === "RUNNING");
      const queued = assigned.filter((task) => task.replay_status === "WAITING");
      const completed = assigned.filter(
        (task) => task.replay_status === "COMPLETED"
      );
  
      return {
        ...vm,
        replay_active_task: active || null,
        replay_queue_count: queued.length,
        replay_completed_count: completed.length,
      };
    });
  
    return {
      time,
      tasks,
      vms,
      waiting_tasks: tasks.filter((task) => task.replay_status === "WAITING")
        .length,
      running_tasks: tasks.filter((task) => task.replay_status === "RUNNING")
        .length,
      completed_tasks: tasks.filter(
        (task) => task.replay_status === "COMPLETED"
      ).length,
    };
  }