import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { listSimulations } from "../services/simulationService";
import "./analytics.css";

const METRICS = [
  { key: "simulated_time", label: "Simulated time", unit: "s" },
  { key: "completed_tasks", label: "Completed tasks", unit: "" },
  { key: "total_tasks", label: "Total tasks", unit: "" },
  { key: "vm_count", label: "Virtual machines", unit: "" },
  { key: "queue_migrations", label: "Queue migrations", unit: "" },
  { key: "completion_percent", label: "Completion", unit: "%" },
];

function number(value) {
  return Number(value || 0);
}

function getSummary(run) {
  const summary = run.summary || run;
  const totalTasks = number(summary.total_tasks ?? summary.task_count);
  const completedTasks = number(summary.completed_tasks);

  return {
    simulated_time: number(summary.simulated_time ?? summary.current_time),
    completed_tasks: completedTasks,
    total_tasks: totalTasks,
    vm_count: number(summary.vm_count ?? summary.total_vms),
    queue_migrations: number(summary.queue_migrations ?? summary.migrations),
    completion_percent: totalTasks
      ? Math.round((completedTasks / totalTasks) * 100)
      : number(summary.completion_percent),
  };
}

function formatValue(value, unit) {
  const formatted = Number.isInteger(value)
    ? value.toString()
    : value.toFixed(2).replace(/\.00$/, "");

  return unit ? `${formatted} ${unit}` : formatted;
}

function RunOption({ run }) {
  const summary = getSummary(run);

  return (
    <option value={run.id}>
      {run.algorithm || "Algorithm"} · {run.id.slice(-8)} · {run.status} ·{" "}
      {summary.completion_percent}%
    </option>
  );
}

export default function Analytics() {
  const { token, user, logout } = useAuth();
  const [runs, setRuns] = useState([]);
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadRuns() {
    setLoading(true);
    setError("");

    try {
      const response = await listSimulations(token, 1, 100);
      const items = response.simulations || response.items || [];
      const completedRuns = items.filter((run) => run.status === "COMPLETED");

      setRuns(completedRuns);

      if (completedRuns.length >= 2) {
        setLeftId((current) => current || completedRuns[0].id);
        setRightId((current) => current || completedRuns[1].id);
      }
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "Unable to load completed simulations."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
  }, []);

  const leftRun = useMemo(
    () => runs.find((run) => run.id === leftId),
    [runs, leftId]
  );

  const rightRun = useMemo(
    () => runs.find((run) => run.id === rightId),
    [runs, rightId]
  );

  const canCompare =
    leftRun &&
    rightRun &&
    leftRun.id !== rightRun.id;

  return (
    <main className="analytics-page">
      <header className="analytics-nav">
        <a className="brand" href="/dashboard">
          LoadLab
          <span>SIMULATION WORKSPACE</span>
        </a>

        <nav>
          <a href="/dashboard">Dashboard</a>
          <a className="active" href="/analytics">Analytics</a>
          <a href="/tasks">Tasks</a>
          <a href="/vms">Virtual machines</a>
        </nav>

        <button type="button" className="sign-out" onClick={logout}>
          Sign out
        </button>
      </header>

      <section className="analytics-content">
        <p className="eyebrow">SIMULATION INSIGHTS</p>
        <div className="analytics-heading">
          <div>
            <h1>Run comparison</h1>
            <p>
              Compare completed simulations for {user?.email || "your account"}.
            </p>
          </div>

          <button type="button" className="refresh-button" onClick={loadRuns}>
            Refresh runs
          </button>
        </div>

        {loading && <p className="analytics-message">Loading completed runs…</p>}
        {error && <p className="analytics-error">{error}</p>}

        {!loading && !error && runs.length < 2 && (
          <section className="empty-comparison">
            <h2>Two completed simulations are required</h2>
            <p>
              Create, start, and complete at least two simulations from the
              Dashboard. They will then appear here for comparison.
            </p>
            <a href="/dashboard">Go to Dashboard</a>
          </section>
        )}

        {!loading && runs.length >= 2 && (
          <>
            <section className="run-selectors">
              <label>
                <span>Baseline run</span>
                <select value={leftId} onChange={(event) => setLeftId(event.target.value)}>
                  {runs.map((run) => <RunOption key={run.id} run={run} />)}
                </select>
              </label>

              <label>
                <span>Comparison run</span>
                <select value={rightId} onChange={(event) => setRightId(event.target.value)}>
                  {runs.map((run) => <RunOption key={run.id} run={run} />)}
                </select>
              </label>
            </section>

            {!canCompare && (
              <p className="analytics-error">
                Select two different completed simulations.
              </p>
            )}

            {canCompare && (
              <>
                <section className="run-overview">
                  {[leftRun, rightRun].map((run, index) => (
                    <article key={run.id} className="run-overview-card">
                      <p>{index === 0 ? "Baseline" : "Comparison"}</p>
                      <h2>{run.algorithm || "Unknown algorithm"}</h2>
                      <span>Simulation {run.id.slice(-8)}</span>
                      <strong>{run.status}</strong>
                    </article>
                  ))}
                </section>

                <section className="metric-grid">
                  {METRICS.map((metric) => {
                    const leftValue = getSummary(leftRun)[metric.key];
                    const rightValue = getSummary(rightRun)[metric.key];
                    const difference = rightValue - leftValue;
                    const direction =
                      difference > 0 ? "higher" : difference < 0 ? "lower" : "same";

                    return (
                      <article className="metric-card" key={metric.key}>
                        <p>{metric.label}</p>
                        <div>
                          <span>{formatValue(leftValue, metric.unit)}</span>
                          <b>vs</b>
                          <span>{formatValue(rightValue, metric.unit)}</span>
                        </div>
                        <strong className={`difference ${direction}`}>
                          {difference > 0 ? "+" : ""}
                          {formatValue(difference, metric.unit)} · {direction}
                        </strong>
                      </article>
                    );
                  })}
                </section>
              </>
            )}
          </>
        )}
      </section>
    </main>
  );
}