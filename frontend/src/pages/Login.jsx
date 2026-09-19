import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { Link } from "react-router-dom";

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
      <main>
        <h1>Signed in</h1>
        <p>{user.email}</p>
        <p>
        <Link to="/tasks">Open Task Management</Link>
        </p>
        <button type="button" onClick={logout}>
          Sign out
        </button>
      </main>
    );
  }

  return (
    <main>
      <h1>Sign in</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
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
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={12}
            maxLength={128}
            disabled={submitting}
            required
          />
        </div>

        {error && <p role="alert">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
      <p>
  Need an account? <Link to="/register">Create an account</Link>
</p>
    </main>
  );
}