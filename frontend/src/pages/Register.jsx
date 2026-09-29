import { useState } from "react";
import { Link } from "react-router-dom";

import { registerUser } from "../services/authService.js";

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
          Create an account to build workloads, configure scheduling
          algorithms, and evaluate load-balancing performance.
        </p>

        <div className="auth-features" aria-label="Platform capabilities">
          <div className="auth-feature">
            <span className="auth-feature-icon" aria-hidden="true">
              ✓
            </span>
            Create reusable simulation scenarios
          </div>

          <div className="auth-feature">
            <span className="auth-feature-icon" aria-hidden="true">
              ✓
            </span>
            Compare algorithm performance and machine utilization
          </div>

          <div className="auth-feature">
            <span className="auth-feature-icon" aria-hidden="true">
              ✓
            </span>
            Export reports and collaborate securely
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [registered, setRegistered] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await registerUser(email, password);
      setPassword("");
      setRegistered(true);
    } catch (err) {
      setError(
        err.response?.data?.error ||
          "Unable to register. Check your connection and try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (registered) {
    return (
      <main className="auth-page">
        <AuthBrand />

        <section className="auth-panel">
          <div className="auth-card">
            <div className="auth-success-icon" aria-hidden="true">
              ✓
            </div>

            <header className="auth-card-header">
              <h2>Account created</h2>
              <p>
                Your account is ready. You can now sign in with your email and
                password.
              </p>
            </header>

            <Link className="auth-secondary-button" to="/login">
              Continue to sign in
            </Link>
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
            <h2>Create your account</h2>
            <p>Start building and comparing load-balancing simulations.</p>
          </header>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="register-email">Email address</label>
              <input
                id="register-email"
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
              <label htmlFor="register-password">Password</label>
              <input
                id="register-password"
                type="password"
                autoComplete="new-password"
                placeholder="Create a secure password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={12}
                maxLength={128}
                aria-describedby="password-help"
                disabled={submitting}
                required
              />

              <p className="auth-help" id="password-help">
                Use between 12 and 128 characters.
              </p>
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
              {submitting ? "Creating account..." : "Create account"}
            </button>
          </form>

          <p className="auth-footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </section>
    </main>
  );
}