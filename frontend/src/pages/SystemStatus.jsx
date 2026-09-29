import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import { getSystemHealth } from "../services/healthService.js";

import "./system-status.css";

function StatusBadge({ value }) {
  const status = String(value || "UNKNOWN").toUpperCase();

  return (
    <span className={`health-badge ${status.toLowerCase()}`}>
      {status}
    </span>
  );
}

function formatUptime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds || 0)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remainingSeconds = total % 60;

  return `${hours}h ${minutes}m ${remainingSeconds}s`;
}

export default function SystemStatus() {
  const { logout } = useAuth();

  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastSuccessfulCheck, setLastSuccessfulCheck] = useState("");

  const refresh = useCallback(async () => {
    const controller = new AbortController();

    setLoading(true);
    setError("");

    try {
      const result = await getSystemHealth(controller.signal);

      setHealth(result);

      if (result.status === "UP") {
        setLastSuccessfulCheck(new Date().toISOString());
      }
    } catch (requestError) {
      setHealth(null);
      setError(
        requestError.message ||
          "The system health endpoint is unavailable."
      );
    } finally {
      setLoading(false);
    }

    return () => controller.abort();
  }, []);

  useEffect(() => {
    refresh();

    const interval = window.setInterval(refresh, 15000);

    return () => window.clearInterval(interval);
  }, [refresh]);

  return (
    <div className="health-page">
      <header className="health-top">
        <Link className="health-brand" to="/dashboard">
          LoadLab <span>Simulation workspace</span>
        </Link>

        <nav aria-label="Main navigation">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/analytics">Analytics</Link>
          <Link to="/reports">Reports</Link>
          <Link to="/replay">Replay</Link>
          <Link to="/status" aria-current="page">
            System status
          </Link>
        </nav>

        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>

      <main className="health-main">
        <p className="health-eyebrow">SYSTEM DIAGNOSTICS</p>

        <div className="health-heading">
          <div>
            <h1>System status</h1>
            <p>
              API and database availability refresh automatically every
              15 seconds.
            </p>
          </div>

          <button
            type="button"
            onClick={refresh}
            disabled={loading}
          >
            {loading ? "Checking…" : "Check now"}
          </button>
        </div>

        {error && (
          <section className="health-alert" role="alert">
            <StatusBadge value="DOWN" />
            <div>
              <h2>Health endpoint unavailable</h2>
              <p>{error}</p>
            </div>
          </section>
        )}

        {health && (
          <>
            <section className="health-overview">
              <article>
                <span>Overall status</span>
                <StatusBadge value={health.status} />
              </article>

              <article>
                <span>Ready for traffic</span>
                <strong>{health.ready ? "Yes" : "No"}</strong>
              </article>

              <article>
                <span>API uptime</span>
                <strong>
                  {formatUptime(health.uptime_seconds)}
                </strong>
              </article>

              <article>
                <span>Environment</span>
                <strong>{health.environment || "development"}</strong>
              </article>
            </section>

            <section className="health-services">
              <h2>Service checks</h2>

              {Object.entries(health.services || {}).map(
                ([name, service]) => (
                  <article key={name}>
                    <div>
                      <h3>
                        {name === "api" ? "Flask API" : "MongoDB"}
                      </h3>
                      <p>{service.message}</p>
                    </div>

                    <StatusBadge value={service.status} />
                  </article>
                )
              )}
            </section>

            <section className="health-meta">
              <h2>Diagnostic details</h2>

              <dl>
                <dt>Backend started</dt>
                <dd>
                  {health.started_at
                    ? new Date(health.started_at).toLocaleString()
                    : "Unavailable"}
                </dd>

                <dt>Latest check</dt>
                <dd>
                  {health.checked_at
                    ? new Date(health.checked_at).toLocaleString()
                    : "Unavailable"}
                </dd>

                <dt>Last successful check</dt>
                <dd>
                  {lastSuccessfulCheck
                    ? new Date(lastSuccessfulCheck).toLocaleString()
                    : "No successful check yet"}
                </dd>
              </dl>
            </section>
          </>
        )}

        {!health && loading && (
          <p className="health-loading">
            Checking API and database availability…
          </p>
        )}
      </main>
    </div>
  );
}