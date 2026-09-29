import { formatReplayTime } from "../services/replayService.js";

export default function ReplayMachines({ frame }) {
  return (
    <section className="replay-panel">
      <p className="replay-eyebrow">VIRTUAL MACHINE WORKLOAD</p>
      <h2>Machine activity at {formatReplayTime(frame.time)} s</h2>

      <div className="replay-machines">
        {frame.vms.map((vm) => (
          <article key={vm.id}>
            <h3>{vm.name}</h3>
            <p>{formatReplayTime(vm.capacity_mips)} MIPS</p>

            <dl>
              <dt>Active task</dt>
              <dd>{vm.replay_active_task?.name || "None"}</dd>

              <dt>Queued tasks</dt>
              <dd>{vm.replay_queue_count}</dd>

              <dt>Completed tasks</dt>
              <dd>{vm.replay_completed_count}</dd>

              <dt>Overload threshold</dt>
              <dd>{formatReplayTime(vm.overload_threshold)} s</dd>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}