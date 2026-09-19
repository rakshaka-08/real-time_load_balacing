import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import TaskTable from "../components/TaskTable.jsx";
import {
  createTask,
  deleteTask,
  generateTasks,
  listTasks,
  updateTask,
} from "../services/taskService.js";
import { Link } from "react-router-dom";

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
  ["min_work_mi", "Minimum work (MI)", 0, undefined, "any"],
  ["max_work_mi", "Maximum work (MI)", 0, undefined, "any"],
  ["min_arrival_time", "Earliest arrival (seconds)", 0, undefined, "any"],
  ["max_arrival_time", "Latest arrival (seconds)", 0, undefined, "any"],
];

function errorMessage(error) {
  return (
    error.response?.data?.error ||
    error.response?.data?.msg ||
    "Request failed. Check that the backend is running and try again."
  );
}

function authenticationFailed(error) {
  return [401, 422].includes(error.response?.status);
}

export default function Tasks() {
  const { user, accessToken, logout } = useAuth();

  const [tasks, setTasks] = useState([]);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [draft, setDraft] = useState({ ...EMPTY_TASK });
  const [editingId, setEditingId] = useState(null);
  const [generation, setGeneration] = useState({
    ...INITIAL_GENERATION,
  });

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const disabled = loading || busy;

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

        if (controller.signal.aborted) return;

        const lastPage = Math.max(1, result.total_pages);

        setTasks(result.tasks);
        setTotal(result.total);

        if (page > lastPage) {
          setPage(lastPage);
        }
      } catch (err) {
        if (controller.signal.aborted) return;

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
  }, [accessToken, page, limit, revision, logout]);

  function resetEditor() {
    setEditingId(null);
    setDraft({ ...EMPTY_TASK });
  }

  async function performAction(action, successMessage) {
    setBusy(true);
    setError("");
    setMessage("");

    try {
      await action();
      setMessage(successMessage);
      setRevision((value) => value + 1);
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
      arrival_time: Number(draft.arrival_time),
    };

    if (!Number.isFinite(payload.work_mi) || payload.work_mi <= 0) {
      setError("Work must be a finite number greater than zero.");
      return;
    }

    if (
      !Number.isFinite(payload.arrival_time) ||
      payload.arrival_time < 0
    ) {
      setError("Arrival time must be a finite number zero or greater.");
      return;
    }

    performAction(async () => {
      if (editingId) {
        await updateTask(accessToken, editingId, payload);
      } else {
        await createTask(accessToken, payload);
        setPage(1);
      }
      resetEditor();
    }, editingId ? "Task updated." : "Task created.");
  }

  function editTask(task) {
    setEditingId(task.id);
    setDraft({
      name: task.name,
      work_mi: String(task.work_mi),
      arrival_time: String(task.arrival_time),
    });
    setError("");
    setMessage("");
    document.getElementById("task-name")?.focus();
  }

  function removeTask(task) {
    if (!window.confirm(`Delete "${task.name}"?`)) return;

    performAction(async () => {
      await deleteTask(accessToken, task.id);
      if (editingId === task.id) resetEditor();
    }, "Task deleted.");
  }

  function generateWorkload(event) {
    event.preventDefault();

    const settings = Object.fromEntries(
      Object.entries(generation).map(([key, value]) => [
        key,
        Number(value),
      ])
    );

    if (!Object.values(settings).every(Number.isFinite)) {
      setError("Generation settings must be finite numbers.");
      return;
    }

    if (settings.min_work_mi <= 0 || settings.max_work_mi <= 0) {
      setError("Both work limits must be greater than zero.");
      return;
    }

    if (
      settings.min_work_mi > settings.max_work_mi ||
      settings.min_arrival_time > settings.max_arrival_time
    ) {
      setError("Each minimum must be no greater than its maximum.");
      return;
    }

    performAction(async () => {
      await generateTasks(accessToken, settings);
      setPage(1);
    }, `${settings.count} tasks generated using seed ${settings.seed}.`);
  }

  return (
    <main>
      <header>
        <h1>Task Management</h1>
        <nav aria-label="Management pages">
     <Link to="/tasks" aria-current="page">Tasks</Link>{" "}
     <Link to="/vms">Virtual Machines</Link>
     </nav>
        <p>Signed in as {user.email}</p>
        <button type="button" onClick={logout} disabled={busy}>
          Sign out
        </button>
      </header>

      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}

      <section aria-labelledby="task-editor-title">
        <h2 id="task-editor-title">
          {editingId ? "Edit task" : "Create task"}
        </h2>

        <form onSubmit={saveTask}>
          <fieldset disabled={disabled}>
            <legend>Task details</legend>

            <p>
              <label htmlFor="task-name">Name </label>
              <input
                id="task-name"
                value={draft.name}
                maxLength={120}
                required
                onChange={(event) =>
                  setDraft({ ...draft, name: event.target.value })
                }
              />
            </p>

            <p>
              <label htmlFor="task-work">Work (million instructions) </label>
              <input
                id="task-work"
                type="number"
                min="0"
                step="any"
                required
                value={draft.work_mi}
                onChange={(event) =>
                  setDraft({ ...draft, work_mi: event.target.value })
                }
              />
            </p>

            <p>
              <label htmlFor="task-arrival">Arrival (seconds) </label>
              <input
                id="task-arrival"
                type="number"
                min="0"
                step="any"
                required
                value={draft.arrival_time}
                onChange={(event) =>
                  setDraft({ ...draft, arrival_time: event.target.value })
                }
              />
            </p>

            <button type="submit">
              {editingId ? "Save changes" : "Create task"}
            </button>{" "}
            {editingId && (
              <button type="button" onClick={resetEditor}>
                Cancel editing
              </button>
            )}
          </fieldset>
        </form>
      </section>

      <section aria-labelledby="generation-title">
        <h2 id="generation-title">Generate workload</h2>
        <p>
          The same settings and seed reproduce work and arrival values.
          Each submission creates new task records.
        </p>

        <form onSubmit={generateWorkload}>
          <fieldset disabled={disabled}>
            <legend>Generation settings</legend>

            {GENERATION_FIELDS.map(([key, label, min, max, step]) => (
              <p key={key}>
                <label htmlFor={`generate-${key}`}>{label} </label>
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
                      [key]: event.target.value,
                    })
                  }
                />
              </p>
            ))}

            <button type="submit">Generate tasks</button>
          </fieldset>
        </form>
      </section>

      <section aria-labelledby="task-list-title" aria-busy={disabled}>
        <h2 id="task-list-title">Saved tasks ({total})</h2>

        <p>
          <label htmlFor="page-size">Tasks per page </label>
          <select
            id="page-size"
            value={limit}
            disabled={disabled}
            onChange={(event) => {
              setLimit(Number(event.target.value));
              setPage(1);
            }}
          >
            {[10, 20, 50, 100].map((size) => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>{" "}
          <button
            type="button"
            disabled={disabled}
            onClick={() => setRevision((value) => value + 1)}
          >
            Refresh
          </button>
        </p>

        {loading ? (
          <p role="status">Loading tasks...</p>
        ) : (
          <TaskTable
            tasks={tasks}
            disabled={busy}
            onEdit={editTask}
            onDelete={removeTask}
          />
        )}

        <nav aria-label="Task pagination">
          <button
            type="button"
            disabled={disabled || page <= 1}
            onClick={() => setPage((value) => value - 1)}
          >
            Previous
          </button>{" "}
          <span>Page {page} of {totalPages}</span>{" "}
          <button
            type="button"
            disabled={disabled || page >= totalPages}
            onClick={() => setPage((value) => value + 1)}
          >
            Next
          </button>
        </nav>
      </section>
    </main>
  );
}