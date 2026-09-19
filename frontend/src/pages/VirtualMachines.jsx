import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import VMTable from "../components/VMTable.jsx";

import {
  createVM,
  deleteVM,
  listVMs,
  updateVM,
} from "../services/vmService.js";


const EMPTY_VM = {
  name: "",
  capacity_mips: "500",
  overload_threshold: "10",
};

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

export default function VirtualMachines() {
  const { user, accessToken, logout } = useAuth();

  const [vms, setVMs] = useState([]);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [draft, setDraft] = useState({ ...EMPTY_VM });
  const [editingId, setEditingId] = useState(null);

  const disabled = loading || busy;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError("");

      try {
        const result = await listVMs(
          accessToken,
          page,
          limit,
          controller.signal
        );

        if (controller.signal.aborted) return;

        setVMs(result.vms);
        setTotal(result.total);

        const lastPage = Math.max(1, result.total_pages);
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
    setDraft({ ...EMPTY_VM });
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

  function saveVM(event) {
    event.preventDefault();

    const payload = {
      name: draft.name.trim(),
      capacity_mips: Number(draft.capacity_mips),
      overload_threshold: Number(draft.overload_threshold),
    };

    if (!payload.name) {
      setError("Enter a VM name.");
      return;
    }

    if (
      !Number.isFinite(payload.capacity_mips) ||
      payload.capacity_mips <= 0
    ) {
      setError("Capacity must be a finite number greater than zero.");
      return;
    }

    if (
      !Number.isFinite(payload.overload_threshold) ||
      payload.overload_threshold <= 0
    ) {
      setError(
        "Overload threshold must be a finite number greater than zero."
      );
      return;
    }

    performAction(async () => {
      if (editingId) {
        await updateVM(accessToken, editingId, payload);
      } else {
        await createVM(accessToken, payload);
        setPage(1);
      }

      resetEditor();
    }, editingId ? "VM updated." : "VM created.");
  }

  function editVM(vm) {
    setEditingId(vm.id);
    setDraft({
      name: vm.name,
      capacity_mips: String(vm.capacity_mips),
      overload_threshold: String(vm.overload_threshold),
    });
    setError("");
    setMessage("");
    document.getElementById("vm-name")?.focus();
  }

  function removeVM(vm) {
    if (!window.confirm(`Delete "${vm.name}"?`)) return;

    performAction(async () => {
      await deleteVM(accessToken, vm.id);
      if (editingId === vm.id) resetEditor();
    }, "VM deleted.");
  }

  return (
    <main>
      <header>
        <h1>Virtual Machines</h1>
        <p>Signed in as {user.email}</p>

        <nav aria-label="Management pages">
          <Link to="/tasks">Tasks</Link>{" "}
          <Link to="/vms" aria-current="page">Virtual Machines</Link>
        </nav>

        <p>
          <button type="button" onClick={logout} disabled={busy}>
            Sign out
          </button>
        </p>
      </header>

      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}

      <section aria-labelledby="vm-editor-title">
        <h2 id="vm-editor-title">
          {editingId ? "Edit virtual machine" : "Create virtual machine"}
        </h2>

        <p>
          Different processing capacities represent heterogeneous machines.
          These records will be used by the simulation engine.
        </p>

        <form onSubmit={saveVM}>
          <fieldset disabled={disabled}>
            <legend>VM details</legend>

            <p>
              <label htmlFor="vm-name">Name </label>
              <input
                id="vm-name"
                value={draft.name}
                maxLength={120}
                required
                onChange={(event) =>
                  setDraft({ ...draft, name: event.target.value })
                }
              />
            </p>

            <p>
              <label htmlFor="vm-capacity">Processing capacity (MIPS) </label>
              <input
                id="vm-capacity"
                type="number"
                min="0"
                step="any"
                required
                value={draft.capacity_mips}
                aria-describedby="capacity-help"
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    capacity_mips: event.target.value,
                  })
                }
              />
            </p>

            <p id="capacity-help">
              A 500 MIPS VM processes 1,000 million instructions in
              2 simulated seconds, excluding queue waiting time.
            </p>

            <p>
              <label htmlFor="vm-threshold">
                Overload threshold (seconds){" "}
              </label>
              <input
                id="vm-threshold"
                type="number"
                min="0"
                step="any"
                required
                value={draft.overload_threshold}
                aria-describedby="threshold-help"
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    overload_threshold: event.target.value,
                  })
                }
              />
            </p>

            <p id="threshold-help">
              During simulation, a VM is overloaded when its remaining
              queued processing time exceeds this value.
            </p>

            <button type="submit">
              {editingId ? "Save changes" : "Create VM"}
            </button>{" "}

            {editingId && (
              <button type="button" onClick={resetEditor}>
                Cancel editing
              </button>
            )}
          </fieldset>
        </form>
      </section>

      <section aria-labelledby="vm-list-title" aria-busy={disabled}>
        <h2 id="vm-list-title">Saved virtual machines ({total})</h2>

        <p>
          <label htmlFor="vm-page-size">VMs per page </label>
          <select
            id="vm-page-size"
            value={limit}
            disabled={disabled}
            onChange={(event) => {
              setLimit(Number(event.target.value));
              setPage(1);
            }}
          >
            {[5, 10, 20, 50, 100].map((size) => (
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
          <p role="status">Loading virtual machines...</p>
        ) : (
          <VMTable
            vms={vms}
            disabled={busy}
            onEdit={editVM}
            onDelete={removeVM}
          />
        )}

        <nav aria-label="VM pagination">
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