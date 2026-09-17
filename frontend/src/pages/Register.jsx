import { useState } from "react";
import { Link } from "react-router-dom";
import { registerUser } from "../services/authService.js";

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
      <main>
        <h1>Account created</h1>
        <p>You can now sign in with your email and password.</p>
        <Link to="/login">Go to sign in</Link>
      </main>
    );
  }

  return (
    <main>
      <h1>Create an account</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="register-email">Email</label>
          <input
            id="register-email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            maxLength={254}
            disabled={submitting}
            required
          />
        </div>

        <div>
          <label htmlFor="register-password">Password</label>
          <input
            id="register-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={12}
            maxLength={128}
            aria-describedby="password-help"
            disabled={submitting}
            required
          />
          <p id="password-help">Use between 12 and 128 characters.</p>
        </div>

        {error && <p role="alert">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Creating account..." : "Create account"}
        </button>
      </form>

      <p>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </main>
  );
}