import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import {
  getSimulation,
  listSimulations,
} from "../services/simulationService.js";

import "./reporting.css";

function errorMessage(error) {
  return (
    error.response?.data?.error ||
    error.response?.data?.msg ||
    "Could not load simulation data. Please try again."
  );
}

function formatNumber(value) {
  if (!Number.isFinite(Number(value))) return "—";

  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function csvValue(value) {
  const text = String(value ?? "");

  return `"${text.replaceAll('"', '""')}"`;
}

function downloadFile(filename, contents, type) {
  const blob = new Blob([contents], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

function makeReport(simulation) {
  return {
    generated_at: new Date().toISOString(),
    simulation: {
      id: simulation.id,
      algorithm: simulation.algorithm,
      status: simulation.status,
      created_at: simulation.created_at,
      simulated_time: simulation.simulated_time,
      total_tasks: simulation.total_tasks,
      completed_tasks: simulation.completed_tasks,
      queue_migrations: simulation.redistribution_count,
      seed: simulation.seed,
      redistribution_enabled: simulation.redistribution_enabled,
    },
    virtual_machines: simulation.vms,
    tasks: simulation.tasks,
  };
}

function createTasksCsv(simulation) {
  const machines = Object.fromEntries(
    simulation.vms.map((vm) => [vm.id, vm.name])
  );

  const rows = [
    [
      "Task ID",
      "Task name",
      "Status",
      "Machine",
      "Remaining work (MI)",
      "Started (s)",
      "Completed (s)",
    ],
    ...simulation.tasks.map((task) => [
      task.id,
      task.name,
      task.status,
      machines[task.vm_id] || "Unassigned",
      task.remaining_work_mi,
      task.started_at,
      task.completed_at,
    ]),
  ];

  return rows.map((row) => row.map(csvValue).join(",")).join("\n");
}

export default function Reporting() {
  const { accessToken, logout } = useAuth();

  const [runs, setRuns] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [simulation, setSimulation] = useState(null);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [error, setError] = useState("");

  const completedTasks = simulation?.completed_tasks || 0;
  const totalTasks = simulation?.total_tasks || 0;
  const completion = totalTasks
    ? Math.round((completedTasks / totalTasks) * 100)
    : 0;

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedId),
    [runs, selectedId]
  );

  const loadRuns = useCallback(async () => {
    const controller = new AbortController();

    setLoadingRuns(true);
    setError("");

    try {
      const result = await listSimulations(
        accessToken,
        1,
        controller.signal
      );

      const completed = (result.simulations || []).filter(
        (run) => run.status === "COMPLETED"
      );

      setRuns(completed);

      if (completed.length && !selectedId) {
        setSelectedId(completed[0].id);
      }
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoadingRuns(false);
    }

    return () => controller.abort();
  }, [accessToken, selectedId]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (!selectedId) {
      setSimulation(null);
      return;
    }

    const controller = new AbortController();

    async function loadReport() {
      setLoadingReport(true);
      setError("");

      try {
        const result = await getSimulation(
          accessToken,
          selectedId,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setSimulation(result);
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(errorMessage(requestError));
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingReport(false);
        }
      }
    }

    loadReport();

    return () => controller.abort();
  }, [accessToken, selectedId]);

  function exportJson() {
    if (!simulation) return;

    const report = JSON.stringify(makeReport(simulation), null, 2);

    downloadFile(
      `simulation-${simulation.id.slice(-8)}-report.json`,
      report,
      "application/json"
    );
  }

  function exportCsv() {
    if (!simulation) return;

    downloadFile(
      `simulation-${simulation.id.slice(-8)}-tasks.csv`,
      createTasksCsv(simulation),
      "text/csv;charset=utf-8"
    );
  }

  return (
    <div className="reporting-page">
      <header className="reporting-top">
        <Link className="reporting-brand" to="/dashboard">
          LoadLab <span>Simulation workspace</span>
        </Link>

        <nav aria-label="Main navigation">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/analytics">Analytics</Link>
          <Link to="/reports" aria-current="page">
            Reports
          </Link>
          <Link to="/tasks">Tasks</Link>
          <Link to="/vms">Virtual machines</Link>
        </nav>

        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>

      <main className="reporting-main">
        <p className="reporting-eyebrow">SIMULATION RESULTS</p>

        <div className="reporting-heading">
          <div>
            <h1>Export a simulation report</h1>
            <p>
              Download completed simulation results as JSON or task data as
              CSV.
            </p>
          </div>

          <button
            type="button"
            onClick={loadRuns}
            disabled={loadingRuns}
          >
            {loadingRuns ? "Refreshing…" : "Refresh runs"}
          </button>
        </div>

        {error && <p className="reporting-error">{error}</p>}

        {!loadingRuns && runs.length === 0 && (
          <section className="reporting-empty">
            <h2>No completed simulations yet</h2>
            <p>
              Create and complete a simulation from the Dashboard before
              exporting a report.
            </p>
            <Link to="/dashboard">Go to Dashboard</Link>
          </section>
        )}

        {runs.length > 0 && (
          <>
            <section className="reporting-picker">
              <label htmlFor="simulation-report">
                Choose a completed simulation
              </label>

              <select
                id="simulation-report"
                value={selectedId}
                onChange={(event) => setSelectedId(event.target.value)}
              >
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.algorithm} · {run.id.slice(-8)} ·{" "}
                    {new Date(run.created_at).toLocaleString()}
                  </option>
                ))}
              </select>
            </section>

            {loadingReport && (
              <p className="reporting-message">Loading report details…</p>
            )}

            {simulation && !loadingReport && (
              <>
                <section className="reporting-summary">
                  <article>
                    <span>Algorithm</span>
                    <strong>{simulation.algorithm}</strong>
                  </article>

                  <article>
                    <span>Simulated time</span>
                    <strong>{formatNumber(simulation.simulated_time)} s</strong>
                  </article>

                  <article>
                    <span>Tasks completed</span>
                    <strong>
                      {completedTasks} / {totalTasks}
                    </strong>
                  </article>

                  <article>
                    <span>Virtual machines</span>
                    <strong>{simulation.vms.length}</strong>
                  </article>

                  <article>
                    <span>Queue migrations</span>
                    <strong>{simulation.redistribution_count}</strong>
                  </article>

                  <article>
                    <span>Completion</span>
                    <strong>{completion}%</strong>
                  </article>
                </section>

                <section className="reporting-actions">
                  <div>
                    <h2>Download results</h2>
                    <p>
                      The JSON report contains the simulation, machines, and
                      tasks. CSV contains one row per executed task.
                    </p>
                  </div>

                  <div>
                    <button type="button" onClick={exportJson}>
                      Download JSON report
                    </button>

                    <button
                      type="button"
                      className="reporting-primary"
                      onClick={exportCsv}
                    >
                      Download task CSV
                    </button>
                  </div>
                </section>

                <section className="reporting-details">
                  <h2>Selected simulation</h2>

                  <dl>
                    <dt>Simulation ID</dt>
                    <dd>{simulation.id}</dd>

                    <dt>Status</dt>
                    <dd>{simulation.status}</dd>

                    <dt>Created</dt>
                    <dd>
                      {new Date(simulation.created_at).toLocaleString()}
                    </dd>

                    <dt>Seed</dt>
                    <dd>{simulation.seed}</dd>

                    <dt>Redistribution</dt>
                    <dd>
                      {simulation.redistribution_enabled
                        ? "Enabled"
                        : "Disabled"}
                    </dd>
                  </dl>
                </section>
              </>
            )}

            {selectedRun && !simulation && !loadingReport && (
              <p className="reporting-message">
                Select {selectedRun.algorithm} again to load its report.
              </p>
            )}
          </>
        )}
      </main>
    </div>
  );
}