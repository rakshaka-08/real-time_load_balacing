import "./virtual-data-center.css";

const MACHINES_PER_RACK = 4;

function number(value) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed.toLocaleString(undefined, {
        maximumFractionDigits: 1,
      })
    : "0";
}

function statusClass(status) {
  return String(status || "idle")
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "-");
}

export default function VirtualDataCenter({
  state,
}) {
  const vms = Array.isArray(state?.vms)
    ? state.vms
    : [];

  const tasks = Array.isArray(
    state?.tasks
  )
    ? state.tasks
    : [];

  const simulatedTime =
    Number(state?.simulated_time) || 0;

  const racks = [];

  for (
    let index = 0;
    index < vms.length;
    index += MACHINES_PER_RACK
  ) {
    racks.push(
      vms.slice(
        index,
        index + MACHINES_PER_RACK
      )
    );
  }

  function taskName(id) {
    return (
      tasks.find((task) => task.id === id)
        ?.name || "No active task"
    );
  }

  return (
    <section className="datacenter-panel">
      <div className="datacenter-heading">
        <div>
          <p>Infrastructure map</p>
          <h3>Virtual data center</h3>
          <span>
            Presentation groups only; the
            scheduler is not rack-aware.
          </span>
        </div>

        <strong>
          {racks.length} visual racks ·{" "}
          {vms.length} VMs
        </strong>
      </div>

      {racks.length ? (
        <div className="rack-grid">
          {racks.map(
            (rack, rackIndex) => (
              <article
                className="rack"
                key={`rack-${rackIndex}`}
              >
                <header>
                  <div>
                    <span>
                      Visual group
                    </span>
                    <h4>
                      Rack {rackIndex + 1}
                    </h4>
                  </div>
                  <b>
                    {rack.length} machines
                  </b>
                </header>

                <div className="rack-machines">
                  {rack.map((vm) => {
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
                      <section
                        className={`rack-machine ${statusClass(
                          vm.status
                        )}`}
                        key={vm.id}
                      >
                        <div>
                          <i />
                          <strong>
                            {vm.name}
                          </strong>
                          <span>
                            {vm.status}
                          </span>
                        </div>

                        <p>
                          {number(
                            vm.capacity_mips
                          )}{" "}
                          MIPS
                        </p>

                        <dl>
                          <dt>Current task</dt>
                          <dd>
                            {taskName(
                              vm.current_task_id
                            )}
                          </dd>

                          <dt>Queue</dt>
                          <dd>
                            {vm.queued_task_ids
                              ?.length || 0}
                          </dd>

                          <dt>Utilization</dt>
                          <dd>
                            {number(
                              utilization
                            )}
                            %
                          </dd>
                        </dl>

                        <div className="machine-load">
                          <span
                            style={{
                              width: `${utilization}%`,
                            }}
                          />
                        </div>
                      </section>
                    );
                  })}
                </div>
              </article>
            )
          )}
        </div>
      ) : (
        <div className="datacenter-empty">
          No virtual machines are available
          in this simulation.
        </div>
      )}
    </section>
  );
}