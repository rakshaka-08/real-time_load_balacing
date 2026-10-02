import "./realtime-overview.css";

function number(value, digits = 1) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) {
    return "0";
  }

  return parsed.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}

function taskCount(tasks, statuses) {
  return tasks.filter((task) =>
    statuses.includes(task.status)
  ).length;
}

function safeClass(value) {
  return String(value || "unknown")
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "-");
}

export default function RealtimeOverview({
  state,
}) {
  const tasks = Array.isArray(state?.tasks)
    ? state.tasks
    : [];

  const vms = Array.isArray(state?.vms)
    ? state.vms
    : [];

  const metrics =
    state?.realtime_metrics ||
    state?.metrics ||
    {};

  const simulatedTime =
    Number(state?.simulated_time) || 0;

  const waiting = taskCount(tasks, [
    "PENDING",
    "WAITING",
    "ASSIGNED",
  ]);
  const running = taskCount(tasks, [
    "RUNNING",
  ]);
  const completed = taskCount(tasks, [
    "COMPLETED",
  ]);
  const failed = taskCount(tasks, [
    "FAILED",
  ]);

  const incoming = tasks.filter((task) => {
    const arrival =
      Number(task.arrival_time) || 0;

    return (
      arrival <= simulatedTime &&
      arrival > Math.max(
        -1,
        simulatedTime - 1
      )
    );
  }).length;

  const activeVMs = vms.filter(
    (vm) =>
      vm.current_task_id ||
      ["RUNNING", "OVERLOADED"].includes(
        vm.status
      )
  ).length;

  const flow = [
    ["Incoming", incoming],
    ["Waiting", waiting],
    ["Running", running],
    ["Completed", completed],
    ["Failed", failed],
  ];

  const flowMaximum = Math.max(
    1,
    ...flow.map(([, value]) => value)
  );

  const recentMigrations = Array.isArray(
    state?.redistributions
  )
    ? state.redistributions.slice(-6).reverse()
    : [];

  function vmName(id) {
    return (
      vms.find((vm) => vm.id === id)
        ?.name ||
      id ||
      "Unknown VM"
    );
  }

  function taskName(id) {
    return (
      tasks.find((task) => task.id === id)
        ?.name ||
      id ||
      "Unknown task"
    );
  }

  return (
    <section
      className="realtime-overview"
      aria-label="Real-time system overview"
    >
      <div className="realtime-summary">
        <article>
          <span>Active VMs</span>
          <strong>
            {activeVMs}
            <small> / {vms.length}</small>
          </strong>
        </article>

        <article>
          <span>Incoming tasks/sec</span>
          <strong>{incoming}</strong>
        </article>

        <article>
          <span>Waiting tasks</span>
          <strong>
            {metrics.backlog_tasks ?? waiting}
          </strong>
        </article>

        <article>
          <span>Backlog</span>
          <strong>
            {number(
              metrics.backlog_work_mi,
              2
            )}
            <small> MI</small>
          </strong>
        </article>

        <article>
          <span>System utilization</span>
          <strong>
            {number(
              metrics.system_utilization,
              2
            )}
            <small>%</small>
          </strong>
        </article>

        <article>
          <span>Load imbalance</span>
          <strong>
            {number(
              metrics.load_imbalance,
              3
            )}
          </strong>
        </article>
      </div>

      <div className="realtime-grid">
        <section className="realtime-card">
          <div className="realtime-heading">
            <div>
              <p>Pipeline</p>
              <h3>Task flow</h3>
            </div>
            <span>
              {number(simulatedTime, 2)}s
            </span>
          </div>

          <div className="task-flow">
            {flow.map(([label, value]) => (
              <div
                className={`task-flow-stage ${safeClass(
                  label
                )}`}
                key={label}
              >
                <div>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
                <div className="task-flow-track">
                  <span
                    style={{
                      width: `${
                        (value / flowMaximum) *
                        100
                      }%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="realtime-card">
          <div className="realtime-heading">
            <div>
              <p>Infrastructure</p>
              <h3>VM utilization</h3>
            </div>
            <span>{vms.length} machines</span>
          </div>

          <div className="vm-utilization-list">
            {vms.length ? (
              vms.map((vm) => {
                const utilization =
                  simulatedTime > 0
                    ? Math.min(
                        100,
                        ((Number(
                          vm.busy_seconds
                        ) || 0) /
                          simulatedTime) *
                          100
                      )
                    : 0;

                return (
                  <article key={vm.id}>
                    <div>
                      <strong>{vm.name}</strong>
                      <span
                        className={`vm-live-status ${safeClass(
                          vm.status
                        )}`}
                      >
                        {vm.status}
                      </span>
                    </div>

                    <div className="vm-live-track">
                      <span
                        style={{
                          width: `${utilization}%`,
                        }}
                      />
                    </div>

                    <small>
                      {number(utilization, 1)}%
                      utilized ·{" "}
                      {vm.queued_task_ids?.length ||
                        0}{" "}
                      queued
                    </small>
                  </article>
                );
              })
            ) : (
              <p>No VM activity available.</p>
            )}
          </div>
        </section>
      </div>

      <section className="realtime-card migration-card">
        <div className="realtime-heading">
          <div>
            <p>Load balancing</p>
            <h3>Redistribution activity</h3>
          </div>
          <span>
            {metrics.redistribution_count ??
              state.redistribution_count ??
              0}{" "}
            total
          </span>
        </div>

        {recentMigrations.length ? (
          <div className="migration-list">
            {recentMigrations.map(
              (migration, index) => {
                const source =
                  migration.source_vm_id ??
                  migration.from_vm_id ??
                  migration.source_vm ??
                  migration.from;

                const destination =
                  migration.destination_vm_id ??
                  migration.to_vm_id ??
                  migration.destination_vm ??
                  migration.to;

                const taskId =
                  migration.task_id ??
                  migration.task;

                const migrationTime =
                  migration.simulated_time ??
                  migration.time ??
                  migration.at;

                return (
                  <article
                    key={`${taskId}-${index}`}
                  >
                    <div>
                      <strong>
                        {taskName(taskId)}
                      </strong>
                      <span>
                        {vmName(source)}
                        <b>→</b>
                        {vmName(destination)}
                      </span>
                    </div>

                    <div>
                      {migration.reason && (
                        <small>
                          {migration.reason}
                        </small>
                      )}
                      {migrationTime != null && (
                        <small>
                          At{" "}
                          {number(
                            migrationTime,
                            2
                          )}
                          s
                        </small>
                      )}
                    </div>
                  </article>
                );
              }
            )}
          </div>
        ) : (
          <div className="migration-empty">
            No task redistributions have been
            recorded for this run.
          </div>
        )}
      </section>
    </section>
  );
}