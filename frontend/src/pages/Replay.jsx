import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import {
  getSimulation,
  listSimulations,
} from "../services/simulationService.js";
import {
  buildReplayState,
  getReplayEndTime,
} from "../services/replayService.js";

import ReplayMachines from "./ReplayMachines.jsx";
import ReplayTimeline from "./ReplayTimeline.jsx";
import "./replay.css";

function errorMessage(error) {
  return (
    error.response?.data?.error ||
    error.response?.data?.msg ||
    "Could not load replay data. Please try again."
  );
}

export default function Replay() {
  const { accessToken, logout } = useAuth();

  const [runs, setRuns] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [simulation, setSimulation] = useState(null);
  const [time, setTime] = useState(0);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingReplay, setLoadingReplay] = useState(false);
  const [error, setError] = useState("");

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

      const completedRuns = (result.simulations || []).filter(
        (run) => run.status === "COMPLETED"
      );

      setRuns(completedRuns);

      if (completedRuns.length && !selectedId) {
        setSelectedId(completedRuns[0].id);
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
      return undefined;
    }

    const controller = new AbortController();

    async function loadSimulation() {
      setLoadingReplay(true);
      setError("");

      try {
        const result = await getSimulation(
          accessToken,
          selectedId,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setSimulation(result);
          setTime(0);
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(errorMessage(requestError));
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingReplay(false);
        }
      }
    }

    loadSimulation();

    return () => controller.abort();
  }, [accessToken, selectedId]);

  const endTime = useMemo(
    () => (simulation ? getReplayEndTime(simulation) : 0),
    [simulation]
  );

  const frame = useMemo(
    () => (simulation ? buildReplayState(simulation, time) : null),
    [simulation, time]
  );

  return (
    <div className="replay-page">
      <header className="replay-top">
        <Link className="replay-brand" to="/dashboard">
          LoadLab <span>Simulation workspace</span>
        </Link>

        <nav aria-label="Main navigation">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/analytics">Analytics</Link>
          <Link to="/reports">Reports</Link>
          <Link to="/replay" aria-current="page">
            Replay
          </Link>
          <Link to="/tasks">Tasks</Link>
          <Link to="/vms">Virtual machines</Link>
        </nav>

        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>

      <main className="replay-main">
        <p className="replay-eyebrow">SIMULATION REPLAY</p>

        <div className="replay-heading">
          <div>
            <h1>Execution timeline</h1>
            <p>
              Move through completed simulation time and inspect task and VM
              activity.
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

        {error && <p className="replay-error">{error}</p>}

        {!loadingRuns && runs.length === 0 && (
          <section className="replay-empty">
            <h2>No completed simulations yet</h2>
            <p>
              Complete a simulation from the Dashboard to replay its execution.
            </p>
            <Link to="/dashboard">Go to Dashboard</Link>
          </section>
        )}

        {runs.length > 0 && (
          <>
            <section className="replay-picker">
              <label htmlFor="replay-run">
                Choose a completed simulation
              </label>

              <select
                id="replay-run"
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

            {loadingReplay && (
              <p className="replay-message">Loading replay data…</p>
            )}

            {frame && !loadingReplay && (
              <div className="replay-layout">
                <ReplayTimeline
                  frame={frame}
                  endTime={endTime}
                  onTimeChange={setTime}
                />

                <ReplayMachines frame={frame} />
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}