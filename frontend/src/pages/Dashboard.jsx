import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import useSimulationSocket from "../hooks/useSimulationSocket.js";
import {
  createSimulation,
  controlSimulation,
  getSimulation,
  listSimulations,
} from "../services/simulationService.js";
import { listTasks } from "../services/taskService.js";
import { listVMs } from "../services/vmService.js";

import "./dashboard.css";

const ALGORITHMS = {
  LPT: {
    name: "Longest Processing Time",
    short: "LPT",
    description:
      "Places longer tasks first. Fast, deterministic, and a useful baseline.",
    parameters: [],
  },
  SPT: {
    name: "Shortest Processing Time",
    short: "SPT",
    description:
      "Places shorter tasks first. Fast, deterministic, and reduces short-job waiting.",
    parameters: [],
  },
  GA: {
    name: "Genetic Algorithm",
    short: "GA",
    description:
      "Searches task orders through selection, crossover, mutation, and elitism.",
    parameters: [
      ["population_size", "Population size", 50, 10, 200],
      ["generations", "Generations", 100, 1, 1000],
      ["crossover_rate", "Crossover rate", 0.9, 0, 1, 0.05],
      ["mutation_rate", "Mutation rate", 0.1, 0, 1, 0.05],
      ["tournament_size", "Tournament size", 3, 1, 50],
      ["elite_count", "Elite count", 2, 1, 50],
    ],
  },
  HBA: {
    name: "Honey Bee Algorithm",
    short: "HBA",
    description:
      "Uses scout bees, selected sites, and neighborhood search to improve task order.",
    parameters: [
      ["scout_bees", "Scout bees", 40, 5, 200],
      ["iterations", "Iterations", 100, 1, 1000],
      ["selected_sites", "Selected sites", 5, 1, 50],
      ["elite_sites", "Elite sites", 2, 1, 50],
      ["elite_recruits", "Elite recruits", 10, 1, 200],
      ["other_recruits", "Other recruits", 5, 1, 200],
      ["neighborhood_moves", "Neighborhood moves", 2, 1, 50],
    ],
  },
};

const ACTIONS = {
  CREATED: ["start", "stop"],
  RUNNING: ["pause", "stop"],
  PAUSED: ["resume", "stop"],
  COMPLETED: ["reset"],
  STOPPED: ["reset"],
  FAILED: ["reset"],
};

function formatNumber(value) {
  if (!Number.isFinite(value)) return "—";

  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function errorMessage(error) {
  return (
    error.response?.data?.error ||
    error.response?.data?.msg ||
    "Could not reach the server. Check your connection and retry."
  );
}

function Badge({ value }) {
  return (
    <span className={`dash-badge ${String(value).toLowerCase()}`}>
      {String(value).replaceAll("_", " ")}
    </span>
  );
}

function InputPicker({
  kind,
  token,
  selected,
  onSelect,
  onError,
}) {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const isTask = kind === "tasks";
  const maximum = isTask ? 500 : 100;

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);

      try {
        const response = await (isTask ? listTasks : listVMs)(
          token,
          page,
          20,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setResult(response);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          onError(error);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => controller.abort();
  }, [token, page, isTask, onError]);

  function toggle(id) {
    if (selected.includes(id)) {
      onSelect(selected.filter((selectedId) => selectedId !== id));
      return;
    }

    onSelect([...selected, id]);
  }

  return (
    <section className="dash-picker">
      <h3>
        {isTask ? "Tasks" : "Virtual machines"}{" "}
        <small>{selected.length} selected</small>
      </h3>

      <p className="dash-muted">
        Choose up to {maximum}. Selections remain selected across pages.
      </p>

      {loading && <p role="status">Loading…</p>}

      {!loading && result?.[kind]?.length === 0 && (
        <p>
          No {isTask ? "tasks" : "VMs"} exist yet.{" "}
          <Link to={isTask ? "/tasks" : "/vms"}>
            Create some first
          </Link>
          .
        </p>
      )}

      <div className="dash-options">
        {result?.[kind]?.map((item) => (
          <label key={item.id}>
            <input
              type="checkbox"
              checked={selected.includes(item.id)}
              disabled={
                !selected.includes(item.id) &&
                selected.length >= maximum
              }
              onChange={() => toggle(item.id)}
            />

            <span>
              {item.name}
              <small>
                {isTask
                  ? `${formatNumber(item.work_mi)} MI · arrives ${formatNumber(
                      item.arrival_time
                    )} s`
                  : `${formatNumber(item.capacity_mips)} MIPS`}
              </small>
            </span>
          </label>
        ))}
      </div>

      <div className="dash-pagination">
        <button
          type="button"
          disabled={loading || page === 1}
          onClick={() => setPage(page - 1)}
        >
          Previous
        </button>

        <span>
          Page {page} / {Math.max(1, result?.total_pages || 1)}
        </span>

        <button
          type="button"
          disabled={
            loading ||
            !result ||
            page >= result.total_pages
          }
          onClick={() => setPage(page + 1)}
        >
          Next
        </button>
      </div>
    </section>
  );
}

function AlgorithmPicker({
  algorithm,
  setAlgorithm,
  parameters,
  setParameters,
}) {
  const config = ALGORITHMS[algorithm];

  function selectAlgorithm(name) {
    const defaults = {};

    for (const [key, , defaultValue] of ALGORITHMS[name].parameters) {
      defaults[key] = String(defaultValue);
    }

    setAlgorithm(name);
    setParameters(defaults);
  }

  function updateParameter(key, value) {
    setParameters((current) => ({
      ...current,
      [key]: value,
    }));
  }

  return (
    <section className="dash-algorithms">
      <h3>Scheduling algorithm</h3>

      <p className="dash-muted">
        Algorithm choice changes only the planned task order.
        Execution and live redistribution remain the same.
      </p>

      <div className="dash-algorithm-grid">
        {Object.entries(ALGORITHMS).map(([key, item]) => (
          <button
            key={key}
            type="button"
            className={`dash-algorithm ${
              algorithm === key ? "selected" : ""
            }`}
            aria-pressed={algorithm === key}
            onClick={() => selectAlgorithm(key)}
          >
            <strong>{item.short}</strong>
            <span>{item.name}</span>
            <small>{item.description}</small>
          </button>
        ))}
      </div>

      {config.parameters.length > 0 && (
        <div className="dash-parameter-panel">
          <h4>{config.short} configuration</h4>

          <div className="dash-parameter-grid">
            {config.parameters.map(
              ([key, label, , minimum, maximum, step = 1]) => (
                <label key={key}>
                  <span>{label}</span>

                  <input
                    type="number"
                    value={parameters[key] ?? ""}
                    min={minimum}
                    max={maximum}
                    step={step}
                    required
                    onChange={(event) =>
                      updateParameter(key, event.target.value)
                    }
                  />

                  <small>
                    Allowed: {minimum} to {maximum}
                  </small>
                </label>
              )
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function NewRun({ token, onCreated, onError }) {
  const [tasks, setTasks] = useState([]);
  const [vms, setVMs] = useState([]);
  const [algorithm, setAlgorithm] = useState("LPT");
  const [parameters, setParameters] = useState({});
  const [seed, setSeed] = useState("42");
  const [redistribution, setRedistribution] = useState(true);
  const [busy, setBusy] = useState(false);

  function validateParameters() {
    for (const [key, label, , minimum, maximum] of ALGORITHMS[
      algorithm
    ].parameters) {
      const value = Number(parameters[key]);

      if (!Number.isFinite(value) || value < minimum || value > maximum) {
        return `${label} must be between ${minimum} and ${maximum}.`;
      }

      if (
        !["crossover_rate", "mutation_rate"].includes(key) &&
        !Number.isInteger(value)
      ) {
        return `${label} must be a whole number.`;
      }
    }

    const numericSeed = Number(seed);

    if (
      !Number.isInteger(numericSeed) ||
      numericSeed < 0 ||
      numericSeed > 4294967295
    ) {
      return "Seed must be a whole number between 0 and 4294967295.";
    }

    return "";
  }

  async function submit(event) {
    event.preventDefault();

    const validationError = validateParameters();

    if (validationError) {
      onError({ response: { data: { error: validationError } } });
      return;
    }

    const normalizedParameters = Object.fromEntries(
      Object.entries(parameters).map(([key, value]) => [
        key,
        Number(value),
      ])
    );

    setBusy(true);

    try {
      const simulation = await createSimulation(
        token,
        tasks,
        vms,
        algorithm,
        normalizedParameters,
        Number(seed),
        redistribution
      );

      onCreated(simulation);
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="dash-panel" onSubmit={submit}>
      <h2>Prepare a simulation</h2>

      <p>
        Select workload inputs, choose a scheduling algorithm,
        then create a saved simulation.
      </p>

      <fieldset disabled={busy}>
        <AlgorithmPicker
          algorithm={algorithm}
          setAlgorithm={setAlgorithm}
          parameters={parameters}
          setParameters={setParameters}
        />

        <div className="dash-run-options">
          <label>
            <span>Random seed</span>

            <input
              type="number"
              min="0"
              max="4294967295"
              step="1"
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
              required
            />
          </label>

          <label className="dash-switch">
            <input
              type="checkbox"
              checked={redistribution}
              onChange={(event) =>
                setRedistribution(event.target.checked)
              }
            />

            <span>
              Enable queue redistribution
              <small>
                Move queued tasks only when another VM can finish them sooner.
              </small>
            </span>
          </label>
        </div>

        <div className="dash-two">
          <InputPicker
            kind="tasks"
            token={token}
            selected={tasks}
            onSelect={setTasks}
            onError={onError}
          />

          <InputPicker
            kind="vms"
            token={token}
            selected={vms}
            onSelect={setVMs}
            onError={onError}
          />
        </div>

        <button
          className="dash-primary"
          disabled={busy || !tasks.length || !vms.length}
        >
          {busy
            ? "Creating…"
            : `Create ${ALGORITHMS[algorithm].short} simulation`}
        </button>
      </fieldset>
    </form>
  );
}

function RunDetail({
  token,
  id,
  onReset,
  onError,
  onChanged,
}) {
  const [restState, setRestState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [refresh, setRefresh] = useState(0);

  const {
    snapshot,
    connectionStatus,
    error,
    reconnect,
  } = useSimulationSocket(id);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);

      try {
        const simulation = await getSimulation(
          token,
          id,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setRestState((current) =>
            !current || simulation.revision >= current.revision
              ? simulation
              : current
          );
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          onError(requestError);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => controller.abort();
  }, [token, id, refresh, onError]);

  const state =
    snapshot && (!restState || snapshot.revision >= restState.revision)
      ? snapshot
      : restState;

  const connected = connectionStatus === "connected";

  async function control(action) {
    setBusy(action);

    try {
      const next = await controlSimulation(token, id, action);

      if (action === "reset") {
        onReset(next);
      } else {
        setRestState((current) =>
          !current || next.revision >= current.revision
            ? next
            : current
        );
      }

      onChanged();
    } catch (requestError) {
      onError(requestError);
      setRefresh((value) => value + 1);
    } finally {
      setBusy("");
    }
  }

  const progress = state?.total_tasks
    ? Math.round((state.completed_tasks / state.total_tasks) * 100)
    : 0;

  return (
    <section className="dash-panel">
      <div className="dash-heading">
        <div>
          <p className="dash-eyebrow">Live monitor</p>
          <h2>Simulation {id.slice(-8)}</h2>
        </div>

        <Badge value={connectionStatus} />
      </div>

      {!connected && (
        <p role="status" className="dash-notice">
          {error || "Connecting to live updates…"}{" "}
          <button type="button" onClick={reconnect}>
            Reconnect
          </button>
        </p>
      )}

      <button
        type="button"
        disabled={loading || Boolean(busy)}
        onClick={() => setRefresh((value) => value + 1)}
      >
        Refresh snapshot
      </button>

      {!state ? (
        <p role="status">
          {loading
            ? "Loading simulation…"
            : "Snapshot unavailable. Retry using Refresh snapshot."}
        </p>
      ) : (
        <>
          <div className="dash-heading dash-run-info">
            <div>
              <Badge value={state.status} />{" "}
              <strong>{state.algorithm}</strong>

              <p className="dash-muted">
                Created {new Date(state.created_at).toLocaleString()}
              </p>

              <p className="dash-muted">
                Seed: {state.seed} · Redistribution:{" "}
                {state.redistribution_enabled ? "enabled" : "disabled"}
              </p>
            </div>

            <div className="dash-controls">
              {(ACTIONS[state.status] || []).map((action) => (
                <button
                  key={action}
                  type="button"
                  className={
                    action === "stop" ? "dash-danger" : "dash-primary"
                  }
                  disabled={Boolean(busy) || !connected}
                  onClick={() => control(action)}
                >
                  {busy === action
                    ? "Saving…"
                    : action === "reset"
                      ? "Reset as new run"
                      : action[0].toUpperCase() + action.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {state.error && (
            <p role="alert" className="dash-alert">
              {state.error}
            </p>
          )}

          <div className="dash-stats">
            <div>
              <span>Simulated time</span>
              <strong>
                {formatNumber(state.simulated_time)} <small>s</small>
              </strong>
            </div>

            <div>
              <span>Tasks completed</span>
              <strong>
                {state.completed_tasks}{" "}
                <small>/ {state.total_tasks}</small>
              </strong>
            </div>

            <div>
              <span>Virtual machines</span>
              <strong>{state.vms.length}</strong>
            </div>

            <div>
              <span>Queue migrations</span>
              <strong>{state.redistribution_count}</strong>
            </div>
          </div>

          <label className="dash-progress">
            Completion · {progress}%
            <progress max="100" value={progress} />
          </label>

          <h3>Machine activity</h3>

          <div className="dash-machines">
            {state.vms.map((vm) => {
              const runningTask = state.tasks.find(
                (task) => task.id === vm.current_task_id
              );

              return (
                <article key={vm.id}>
                  <div className="dash-heading">
                    <h4>{vm.name}</h4>
                    <Badge value={vm.status} />
                  </div>

                  <p>{formatNumber(vm.capacity_mips)} MIPS</p>

                  <dl>
                    <dt>Current task</dt>
                    <dd>{runningTask?.name || "None"}</dd>

                    <dt>Queued tasks</dt>
                    <dd>{vm.queued_task_ids.length}</dd>

                    <dt>Queued work</dt>
                    <dd>{formatNumber(vm.queued_seconds)} s</dd>

                    <dt>Overload threshold</dt>
                    <dd>{formatNumber(vm.overload_threshold)} s</dd>

                    <dt>Busy time</dt>
                    <dd>{formatNumber(vm.busy_seconds)} s</dd>
                  </dl>
                </article>
              );
            })}
          </div>

          <h3>Task execution</h3>

          <div
            className="dash-table-scroll"
            tabIndex="0"
            role="region"
            aria-label="Task execution table"
          >
            <table>
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Status</th>
                  <th>Machine</th>
                  <th>Remaining MI</th>
                  <th>Started (s)</th>
                  <th>Completed (s)</th>
                </tr>
              </thead>

              <tbody>
                {state.tasks.map((task) => {
                  const vm = state.vms.find(
                    (candidate) => candidate.id === task.vm_id
                  );

                  return (
                    <tr key={task.id}>
                      <td>{task.name}</td>
                      <td>
                        <Badge value={task.status} />
                      </td>
                      <td>{vm?.name || "Unassigned"}</td>
                      <td>{formatNumber(task.remaining_work_mi)}</td>
                      <td>{formatNumber(task.started_at)}</td>
                      <td>{formatNumber(task.completed_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

export default function Dashboard() {
  const { user, accessToken, logout } = useAuth();

  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("run");

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refresh, setRefresh] = useState(0);

  const onError = useCallback(
    (requestError) => {
      if ([401, 422].includes(requestError.response?.status)) {
        logout();
        return;
      }

      setError(errorMessage(requestError));
    },
    [logout]
  );

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);

      try {
        const response = await listSimulations(
          accessToken,
          page,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setResult(response);
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          onError(requestError);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => controller.abort();
  }, [accessToken, page, refresh, onError]);

  function select(run) {
    setError("");
    setCreating(false);
    setSearchParams({ run: run.id });
  }

  function created(run) {
    select(run);
    setPage(1);
    setRefresh((value) => value + 1);
  }

  return (
    <div className="dashboard">
      <header className="dash-top">
        <Link className="dash-brand" to="/dashboard">
          LoadLab <span>Simulation workspace</span>
        </Link>

        <nav aria-label="Main navigation">
          <Link to="/dashboard" aria-current="page">
            Dashboard
          </Link>

          <Link to="/tasks">Tasks</Link>
          <Link to="/vms">Virtual machines</Link>
        </nav>

        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>

      <main className="dash-main">
        <div className="dash-heading">
          <div>
            <p className="dash-eyebrow">
              Distributed systems / Live workspace
            </p>

            <h1>Simulation dashboard</h1>

            <p className="dash-muted">
              Watch work move across your machines. Signed in as {user.email}.
            </p>
          </div>

          <button
            type="button"
            className="dash-primary"
            onClick={() => {
              setError("");
              setCreating((current) => !current);
            }}
          >
            {creating ? "Close setup" : "New simulation"}
          </button>
        </div>

        {error && (
          <div role="alert" className="dash-alert">
            {error}{" "}
            <button type="button" onClick={() => setError("")}>
              Dismiss
            </button>
          </div>
        )}

        {creating && (
          <NewRun
            token={accessToken}
            onCreated={created}
            onError={onError}
          />
        )}

        <div className="dash-layout">
          <aside className="dash-panel">
            <div className="dash-heading">
              <h2>Saved runs</h2>

              <button
                type="button"
                disabled={loading}
                onClick={() => setRefresh((value) => value + 1)}
              >
                Refresh
              </button>
            </div>

            <p className="dash-muted">
              Select a run to monitor it live.
            </p>

            {loading ? (
              <p role="status">Loading runs…</p>
            ) : result?.simulations.length ? (
              result.simulations.map((run) => (
                <button
                  key={run.id}
                  type="button"
                  className={`dash-run ${
                    selectedId === run.id ? "selected" : ""
                  }`}
                  aria-pressed={selectedId === run.id}
                  onClick={() => select(run)}
                >
                  <strong>
                    {run.algorithm} · {run.id.slice(-8)}
                  </strong>

                  <Badge value={run.status} />

                  <small>
                    {new Date(run.created_at).toLocaleString()}
                  </small>
                </button>
              ))
            ) : (
              <p>No runs exist yet. Create a simulation to begin.</p>
            )}

            <div className="dash-pagination">
              <button
                type="button"
                disabled={loading || page === 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>

              <span>
                {page} / {Math.max(1, result?.total_pages || 1)}
              </span>

              <button
                type="button"
                disabled={
                  loading ||
                  !result ||
                  page >= result.total_pages
                }
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </aside>

          {selectedId ? (
            <RunDetail
              key={selectedId}
              token={accessToken}
              id={selectedId}
              onReset={created}
              onError={onError}
              onChanged={() => setRefresh((value) => value + 1)}
            />
          ) : (
            <section className="dash-panel dash-empty">
              <span className="dash-empty-icon">◫</span>
              <h2>Your next run starts here</h2>
              <p>
                Select a saved simulation or create one using your tasks and
                virtual machines.
              </p>

              <button
                type="button"
                className="dash-primary"
                onClick={() => setCreating(true)}
              >
                Prepare a simulation
              </button>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}