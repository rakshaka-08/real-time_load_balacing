import { Component } from "react";

import "../pages/app-error.css";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Application rendering failed.", {
      error,
      errorInfo,
    });
  }

  retry = () => {
    this.setState({
      hasError: false,
      error: null,
    });

    window.location.reload();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main className="app-error-page">
        <section className="app-error-card" role="alert">
          <p className="app-error-eyebrow">APPLICATION ERROR</p>
          <h1>Something went wrong</h1>

          <p>
            The interface could not finish loading. Your saved tasks,
            virtual machines, simulations, and templates are unchanged.
          </p>

          {import.meta.env.DEV && this.state.error?.message && (
            <pre>{this.state.error.message}</pre>
          )}

          <div className="app-error-actions">
            <button type="button" onClick={this.retry}>
              Reload application
            </button>

            <a href="/login">Return to sign in</a>
          </div>
        </section>
      </main>
    );
  }
}