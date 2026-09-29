import { Link } from "react-router-dom";

import "./app-error.css";

export default function NotFound() {
  return (
    <main className="app-error-page">
      <section className="app-error-card">
        <p className="app-error-eyebrow">ERROR 404</p>
        <h1>Page not found</h1>

        <p>
          The address you opened does not match a page in the LoadLab
          workspace.
        </p>

        <div className="app-error-actions">
          <Link className="app-error-primary" to="/dashboard">
            Go to Dashboard
          </Link>

          <Link to="/login">Go to sign in</Link>
        </div>
      </section>
    </main>
  );
}