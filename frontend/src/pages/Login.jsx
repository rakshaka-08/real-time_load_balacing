import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";

import "./auth.css";

function AuthBrand() {
  return (
    <section className="auth-brand" aria-label="Application information">
      <div className="auth-brand-content">
        <div className="auth-logo">
          <span className="auth-logo-mark" aria-hidden="true">
            LL
          </span>

          <span className="auth-logo-text">
            <strong>LoadLab</strong>
            <span>Simulation workspace</span>
          </span>
        </div>

        <p className="auth-eyebrow">Distributed systems laboratory</p>
        <h1>Intelligent Load Balancing Simulator</h1>

        <p className="auth-description">
          Design workloads, compare scheduling algorithms, and monitor task
          execution across distributed virtual machines in real time.
        </p>

        <div className="auth-features" aria-label="Platform capabilities">
          <div className="auth-feature">
            <span className="auth-feature-icon" aria-hidden="true">
              ✓
            </span>
            Compare GA, HBA, Hybrid GA + HBA, LPT, and SPT
          </div>

          <div className="auth-feature">
            <span className="auth-feature-icon" aria-hidden="true">
              ✓
            </span>
            Monitor live workloads and virtual machines
          </div>

          <div className="auth-feature">
            <span className="auth-feature-icon" aria-hidden="true">
              ✓
            </span>
            Analyze, replay, export, and share simulation results
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Login() {
  const { user, login, logout } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login(email, password);
      setPassword("");
    } catch (err) {
      setError(
        err.response?.data?.error ||
          "Unable to sign in. Check your connection and try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (user) {
    return (
      <main className="auth-page">
        <AuthBrand />

        <section className="auth-panel">
          <div className="auth-card">
            <div className="auth-success-icon" aria-hidden="true">
              ✓
            </div>

            <header className="auth-card-header">
              <h2>You are signed in</h2>
              <p>Continue to your simulation workspace.</p>
              <p className="auth-session-email">{user.email}</p>
            </header>

            <div className="auth-session-actions">
              <Link className="auth-secondary-button" to="/dashboard">
                Open dashboard
              </Link>

              <button
                className="auth-signout"
                type="button"
                onClick={logout}
              >
                Sign out
              </button>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-page">
      <AuthBrand />

      <section className="auth-panel">
        <div className="auth-card">
          <header className="auth-card-header">
            <h2>Welcome back</h2>
            <p>Sign in to open your simulation workspace.</p>
          </header>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                autoComplete="username"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                maxLength={254}
                disabled={submitting}
                required
                autoFocus
              />
            </div>

            <div className="auth-field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={12}
                maxLength={128}
                disabled={submitting}
                required
              />
            </div>

            {error && (
              <p className="auth-error" role="alert">
                {error}
              </p>
            )}

            <button
              className="auth-submit"
              type="submit"
              disabled={submitting}
            >
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="auth-footer">
            Need an account? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </section>
    </main>
  );
}