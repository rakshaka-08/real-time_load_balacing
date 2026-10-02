import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import TaskTable from "../components/TaskTable.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  createTask,
  deleteTask,
  generateTasks,
  listTasks,
  updateTask,
} from "../services/taskService.js";

import "./tasks.css";

const EMPTY_TASK = {
  name: "",
  work_mi: "1000",
  arrival_time: "0",
};

const INITIAL_GENERATION = {
  count: "50",
  seed: "42",
  min_work_mi: "100",
  max_work_mi: "1000",
  min_arrival_time: "0",
  max_arrival_time: "0",
};

const GENERATION_FIELDS = [
  ["count", "Task count", 1, 1000, "1"],
  ["seed", "Random seed", 0, 4294967295, "1"],
  [
    "min_work_mi",
    "Minimum work (MI)",
    0,
    undefined,
    "any",
  ],
  [
    "max_work_mi",
    "Maximum work (MI)",
    0,
    undefined,
    "any",
  ],
  [
    "min_arrival_time",
    "Earliest arrival (seconds)",
    0,
    undefined,
    "any",
  ],
  [
    "max_arrival_time",
    "Latest arrival (seconds)",
    0,
    undefined,
    "any",
  ],
];

function errorMessage(error) {
  return (
    error.response?.data?.error ||
    error.response?.data?.msg ||
    "Request failed. Check that the backend is running and try again."
  );
}

function authenticationFailed(error) {
  return [401, 422].includes(
    error.response?.status
  );
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(
    Number(value) || 0
  );
}

export default function Tasks() {
  const {
    user,
    accessToken,
    logout,
  } = useAuth();

  const [tasks, setTasks] = useState([]);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [draft, setDraft] = useState({
    ...EMPTY_TASK,
  });
  const [editingId, setEditingId] = (
    useState(null)
  );
  const [generation, setGeneration] = (
    useState({
      ...INITIAL_GENERATION,
    })
  );

  const totalPages = Math.max(
    1,
    Math.ceil(total / limit)
  );
  const disabled = loading || busy;

  const visibleWork = tasks.reduce(
    (sum, task) =>
      sum + (Number(task.work_mi) || 0),
    0
  );

  const delayedTasks = tasks.filter(
    (task) =>
      Number(task.arrival_time) > 0
  ).length;

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError("");

      try {
        const result = await listTasks(
          accessToken,
          page,
          limit,
          controller.signal
        );

        if (controller.signal.aborted) {
          return;
        }

        const lastPage = Math.max(
          1,
          result.total_pages
        );

        setTasks(result.tasks);
        setTotal(result.total);

        if (page > lastPage) {
          setPage(lastPage);
        }
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }

        if (authenticationFailed(err)) {
          logout();
          return;
        }

        setError(errorMessage(err));
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => controller.abort();
  }, [
    accessToken,
    page,
    limit,
    revision,
    logout,
  ]);

  function resetEditor() {
    setEditingId(null);
    setDraft({
      ...EMPTY_TASK,
    });
  }

  async function performAction(
    action,
    successMessage
  ) {
    setBusy(true);
    setError("");
    setMessage("");

    try {
      await action();
      setMessage(successMessage);
      setRevision(
        (value) => value + 1
      );
    } catch (err) {
      if (authenticationFailed(err)) {
        logout();
      } else {
        setError(errorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  }

  function saveTask(event) {
    event.preventDefault();

    const payload = {
      name: draft.name.trim(),
      work_mi: Number(draft.work_mi),
      arrival_time: Number(
        draft.arrival_time
      ),
    };

    if (
      !Number.isFinite(payload.work_mi) ||
      payload.work_mi <= 0
    ) {
      setError(
        "Work must be a finite number greater than zero."
      );
      return;
    }

    if (
      !Number.isFinite(
        payload.arrival_time
      ) ||
      payload.arrival_time < 0
    ) {
      setError(
        "Arrival time must be a finite number zero or greater."
      );
      return;
    }

    performAction(
      async () => {
        if (editingId) {
          await updateTask(
            accessToken,
            editingId,
            payload
          );
        } else {
          await createTask(
            accessToken,
            payload
          );
          setPage(1);
        }

        resetEditor();
      },
      editingId
        ? "Task updated."
        : "Task created."
    );
  }

  function editTask(task) {
    setEditingId(task.id);
    setDraft({
      name: task.name,
      work_mi: String(task.work_mi),
      arrival_time: String(
        task.arrival_time
      ),
    });
    setError("");
    setMessage("");

    window.setTimeout(() => {
      document
        .getElementById("task-name")
        ?.focus();
    }, 0);
  }

  function removeTask(task) {
    if (
      !window.confirm(
        `Delete "${task.name}"?`
      )
    ) {
      return;
    }

    performAction(
      async () => {
        await deleteTask(
          accessToken,
          task.id
        );

        if (editingId === task.id) {
          resetEditor();
        }
      },
      "Task deleted."
    );
  }

  function generateWorkload(event) {
    event.preventDefault();

    const settings = Object.fromEntries(
      Object.entries(generation).map(
        ([key, value]) => [
          key,
          Number(value),
        ]
      )
    );

    if (
      !Object.values(settings).every(
        Number.isFinite
      )
    ) {
      setError(
        "Generation settings must be finite numbers."
      );
      return;
    }

    if (
      settings.min_work_mi <= 0 ||
      settings.max_work_mi <= 0
    ) {
      setError(
        "Both work limits must be greater than zero."
      );
      return;
    }

    if (
      settings.min_work_mi >
        settings.max_work_mi ||
      settings.min_arrival_time >
        settings.max_arrival_time
    ) {
      setError(
        "Each minimum must be no greater than its maximum."
      );
      return;
    }

    performAction(
      async () => {
        await generateTasks(
          accessToken,
          settings
        );
        setPage(1);
      },
      `${settings.count} tasks generated using seed ${settings.seed}.`
    );
  }

  return (
    <main className="tasks-page">
      <header className="tasks-header">
        <div className="tasks-brand">
          <Link
            to="/dashboard"
            className="tasks-brand-name"
          >
            LoadLab
          </Link>
          <span>Simulation workspace</span>
        </div>

        <nav
          className="tasks-navigation"
          aria-label="Management pages"
        >
          <Link to="/dashboard">
            Dashboard
          </Link>
          <Link
            to="/tasks"
            aria-current="page"
          >
            Tasks
          </Link>
          <Link to="/vms">
            Virtual machines
          </Link>
        </nav>

        <div className="tasks-account">
          <span title={user.email}>
            {user.email}
          </span>
          <button
            type="button"
            className="tasks-button secondary"
            onClick={logout}
            disabled={busy}
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="tasks-content">
        <section className="tasks-hero">
          <div>
            <p className="tasks-eyebrow">
              Workload management
            </p>
            <h1>Tasks</h1>
            <p className="tasks-introduction">
              Create individual work items or
              generate deterministic workloads
              for simulation experiments.
            </p>
          </div>

          <div
            className="tasks-state"
            aria-live="polite"
          >
            <span
              className={
                loading || busy
                  ? "state-dot active"
                  : "state-dot"
              }
            />
            {loading
              ? "Loading tasks"
              : busy
                ? "Saving changes"
                : "Workspace ready"}
          </div>
        </section>

        {error && (
          <div
            className="tasks-alert error"
            role="alert"
          >
            <strong>Request failed</strong>
            <span>{error}</span>
          </div>
        )}

        {message && (
          <div
            className="tasks-alert success"
            role="status"
          >
            <strong>Success</strong>
            <span>{message}</span>
          </div>
        )}

        <section
          className="tasks-summary"
          aria-label="Task summary"
        >
          <article>
            <span>Saved tasks</span>
            <strong>
              {formatNumber(total)}
            </strong>
            <small>
              Available for simulations
            </small>
          </article>

          <article>
            <span>Visible workload</span>
            <strong>
              {formatNumber(visibleWork)}
            </strong>
            <small>
              Million instructions
            </small>
          </article>

          <article>
            <span>Delayed arrivals</span>
            <strong>
              {formatNumber(delayedTasks)}
            </strong>
            <small>
              On the current page
            </small>
          </article>

          <article>
            <span>Current page</span>
            <strong>
              {page} / {totalPages}
            </strong>
            <small>
              {tasks.length} records visible
            </small>
          </article>
        </section>

        <div className="tasks-workspace">
          <section
            className="tasks-card"
            aria-labelledby="task-editor-title"
          >
            <div className="tasks-card-heading">
              <div>
                <p className="tasks-card-label">
                  Single task
                </p>
                <h2 id="task-editor-title">
                  {editingId
                    ? "Edit task"
                    : "Create task"}
                </h2>
              </div>

              {editingId && (
                <span className="tasks-badge">
                  Editing
                </span>
              )}
            </div>

            <form onSubmit={saveTask}>
              <fieldset disabled={disabled}>
                <legend className="sr-only">
                  Task details
                </legend>

                <div className="tasks-field full">
                  <label htmlFor="task-name">
                    Task name
                  </label>
                  <input
                    id="task-name"
                    value={draft.name}
                    maxLength={120}
                    placeholder="Example: Image processing"
                    required
                    onChange={(event) =>
                      setDraft({
                        ...draft,
                        name: event.target.value,
                      })
                    }
                  />
                </div>

                <div className="tasks-form-grid">
                  <div className="tasks-field">
                    <label htmlFor="task-work">
                      Workload
                    </label>
                    <div className="tasks-input-unit">
                      <input
                        id="task-work"
                        type="number"
                        min="0"
                        step="any"
                        required
                        value={draft.work_mi}
                        onChange={(event) =>
                          setDraft({
                            ...draft,
                            work_mi:
                              event.target.value,
                          })
                        }
                      />
                      <span>MI</span>
                    </div>
                  </div>

                  <div className="tasks-field">
                    <label htmlFor="task-arrival">
                      Arrival time
                    </label>
                    <div className="tasks-input-unit">
                      <input
                        id="task-arrival"
                        type="number"
                        min="0"
                        step="any"
                        required
                        value={
                          draft.arrival_time
                        }
                        onChange={(event) =>
                          setDraft({
                            ...draft,
                            arrival_time:
                              event.target.value,
                          })
                        }
                      />
                      <span>sec</span>
                    </div>
                  </div>
                </div>

                <div className="tasks-form-actions">
                  <button
                    type="submit"
                    className="tasks-button primary"
                  >
                    {editingId
                      ? "Save changes"
                      : "Create task"}
                  </button>

                  {editingId && (
                    <button
                      type="button"
                      className="tasks-button secondary"
                      onClick={resetEditor}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </fieldset>
            </form>
          </section>

          <section
            className="tasks-card generation-card"
            aria-labelledby="generation-title"
          >
            <div className="tasks-card-heading">
              <div>
                <p className="tasks-card-label">
                  Batch creation
                </p>
                <h2 id="generation-title">
                  Generate workload
                </h2>
              </div>

              <span className="tasks-badge">
                Seeded
              </span>
            </div>

            <p className="tasks-card-description">
              Reuse the same settings and seed
              to reproduce work and arrival
              values.
            </p>

            <form onSubmit={generateWorkload}>
              <fieldset disabled={disabled}>
                <legend className="sr-only">
                  Generation settings
                </legend>

                <div className="generation-grid">
                  {GENERATION_FIELDS.map(
                    ([
                      key,
                      label,
                      min,
                      max,
                      step,
                    ]) => (
                      <div
                        className="tasks-field"
                        key={key}
                      >
                        <label
                          htmlFor={`generate-${key}`}
                        >
                          {label}
                        </label>
                        <input
                          id={`generate-${key}`}
                          type="number"
                          min={min}
                          max={max}
                          step={step}
                          required
                          value={generation[key]}
                          onChange={(event) =>
                            setGeneration({
                              ...generation,
                              [key]:
                                event.target
                                  .value,
                            })
                          }
                        />
                      </div>
                    )
                  )}
                </div>

                <div className="tasks-form-actions">
                  <button
                    type="submit"
                    className="tasks-button primary"
                  >
                    Generate tasks
                  </button>
                </div>
              </fieldset>
            </form>
          </section>
        </div>

        <section
          className="tasks-card task-list-card"
          aria-labelledby="task-list-title"
          aria-busy={disabled}
        >
          <div className="task-list-toolbar">
            <div>
              <p className="tasks-card-label">
                Task library
              </p>
              <h2 id="task-list-title">
                Saved tasks
                <span> {total}</span>
              </h2>
            </div>

            <div className="task-list-controls">
              <label htmlFor="page-size">
                Per page
              </label>
              <select
                id="page-size"
                value={limit}
                disabled={disabled}
                onChange={(event) => {
                  setLimit(
                    Number(event.target.value)
                  );
                  setPage(1);
                }}
              >
                {[10, 20, 50, 100].map(
                  (size) => (
                    <option
                      key={size}
                      value={size}
                    >
                      {size}
                    </option>
                  )
                )}
              </select>

              <button
                type="button"
                className="tasks-button secondary"
                disabled={disabled}
                onClick={() =>
                  setRevision(
                    (value) => value + 1
                  )
                }
              >
                Refresh
              </button>
            </div>
          </div>

          {loading ? (
            <div
              className="tasks-loading"
              role="status"
            >
              <span className="tasks-spinner" />
              <p>Loading task records…</p>
            </div>
          ) : tasks.length ? (
            <div className="task-table-wrapper">
              <TaskTable
                tasks={tasks}
                disabled={busy}
                onEdit={editTask}
                onDelete={removeTask}
              />
            </div>
          ) : (
            <div className="tasks-empty">
              <span>0</span>
              <h3>No tasks saved</h3>
              <p>
                Create a task or generate a
                workload to begin.
              </p>
            </div>
          )}

          <nav
            className="tasks-pagination"
            aria-label="Task pagination"
          >
            <button
              type="button"
              className="tasks-button secondary"
              disabled={
                disabled || page <= 1
              }
              onClick={() =>
                setPage(
                  (value) => value - 1
                )
              }
            >
              Previous
            </button>

            <span>
              Page <strong>{page}</strong> of{" "}
              <strong>{totalPages}</strong>
            </span>

            <button
              type="button"
              className="tasks-button secondary"
              disabled={
                disabled ||
                page >= totalPages
              }
              onClick={() =>
                setPage(
                  (value) => value + 1
                )
              }
            >
              Next
            </button>
          </nav>
        </section>
      </div>
    </main>
  );
}