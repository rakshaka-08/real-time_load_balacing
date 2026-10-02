import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import {
  createVM,
  deleteVM,
  listVMs,
  updateVM,
} from "../services/vmService.js";

import "./virtual-machines.css";

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
  return [401, 422].includes(
    error.response?.status
  );
}

function formatNumber(value) {
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 2,
  }).format(Number(value) || 0);
}

export default function VirtualMachines() {
  const {
    user,
    accessToken,
    logout,
  } = useAuth();

  const [vms, setVMs] = useState([]);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [draft, setDraft] = useState({
    ...EMPTY_VM,
  });
  const [editingId, setEditingId] = (
    useState(null)
  );

  const disabled = loading || busy;
  const totalPages = Math.max(
    1,
    Math.ceil(total / limit)
  );

  const visibleCapacity = vms.reduce(
    (sum, vm) =>
      sum + (Number(vm.capacity_mips) || 0),
    0
  );

  const averageCapacity = vms.length
    ? visibleCapacity / vms.length
    : 0;

  const averageThreshold = vms.length
    ? vms.reduce(
        (sum, vm) =>
          sum +
          (Number(vm.overload_threshold) || 0),
        0
      ) / vms.length
    : 0;

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

        if (controller.signal.aborted) {
          return;
        }

        setVMs(result.vms);
        setTotal(result.total);

        const lastPage = Math.max(
          1,
          result.total_pages
        );

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
    setDraft({ ...EMPTY_VM });
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

  function saveVM(event) {
    event.preventDefault();

    const payload = {
      name: draft.name.trim(),
      capacity_mips: Number(
        draft.capacity_mips
      ),
      overload_threshold: Number(
        draft.overload_threshold
      ),
    };

    if (!payload.name) {
      setError("Enter a VM name.");
      return;
    }

    if (
      !Number.isFinite(
        payload.capacity_mips
      ) ||
      payload.capacity_mips <= 0
    ) {
      setError(
        "Capacity must be a finite number greater than zero."
      );
      return;
    }

    if (
      !Number.isFinite(
        payload.overload_threshold
      ) ||
      payload.overload_threshold <= 0
    ) {
      setError(
        "Overload threshold must be a finite number greater than zero."
      );
      return;
    }

    performAction(
      async () => {
        if (editingId) {
          await updateVM(
            accessToken,
            editingId,
            payload
          );
        } else {
          await createVM(
            accessToken,
            payload
          );
          setPage(1);
        }

        resetEditor();
      },
      editingId
        ? "VM updated."
        : "VM created."
    );
  }

  function editVM(vm) {
    setEditingId(vm.id);
    setDraft({
      name: vm.name,
      capacity_mips: String(
        vm.capacity_mips
      ),
      overload_threshold: String(
        vm.overload_threshold
      ),
    });
    setError("");
    setMessage("");

    window.setTimeout(() => {
      document
        .getElementById("vm-name")
        ?.focus();
    }, 0);
  }

  function removeVM(vm) {
    if (
      !window.confirm(
        `Delete "${vm.name}"?`
      )
    ) {
      return;
    }

    performAction(
      async () => {
        await deleteVM(
          accessToken,
          vm.id
        );

        if (editingId === vm.id) {
          resetEditor();
        }
      },
      "VM deleted."
    );
  }

  return (
    <main className="vms-page">
      <header className="vms-header">
        <div className="vms-brand">
          <Link to="/dashboard">
            LoadLab
          </Link>
          <span>Simulation workspace</span>
        </div>

        <nav aria-label="Management pages">
          <Link to="/dashboard">
            Dashboard
          </Link>
          <Link to="/tasks">
            Tasks
          </Link>
          <Link
            to="/vms"
            aria-current="page"
          >
            Virtual machines
          </Link>
        </nav>

        <div className="vms-account">
          <span>{user.email}</span>
          <button
            type="button"
            className="vms-button secondary"
            onClick={logout}
            disabled={busy}
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="vms-content">
        <section className="vms-hero">
          <div>
            <p className="vms-eyebrow">
              Infrastructure management
            </p>
            <h1>Virtual machines</h1>
            <p>
              Configure heterogeneous processing
              capacity and overload limits for
              simulation experiments.
            </p>
          </div>

          <span className="vms-ready">
            <i
              className={
                disabled ? "active" : ""
              }
            />
            {loading
              ? "Loading"
              : busy
                ? "Saving"
                : "Workspace ready"}
          </span>
        </section>

        {error && (
          <div
            className="vms-alert error"
            role="alert"
          >
            <strong>Request failed</strong>
            <span>{error}</span>
          </div>
        )}

        {message && (
          <div
            className="vms-alert success"
            role="status"
          >
            <strong>Success</strong>
            <span>{message}</span>
          </div>
        )}

        <section
          className="vms-summary"
          aria-label="VM summary"
        >
          <article>
            <span>Saved machines</span>
            <strong>
              {formatNumber(total)}
            </strong>
            <small>
              Available for simulations
            </small>
          </article>

          <article>
            <span>Visible capacity</span>
            <strong>
              {formatNumber(visibleCapacity)}
            </strong>
            <small>Total MIPS on this page</small>
          </article>

          <article>
            <span>Average capacity</span>
            <strong>
              {formatNumber(averageCapacity)}
            </strong>
            <small>MIPS per visible VM</small>
          </article>

          <article>
            <span>Average threshold</span>
            <strong>
              {formatNumber(averageThreshold)}
            </strong>
            <small>Queued seconds</small>
          </article>
        </section>

        <div className="vms-workspace">
          <section
            className="vms-panel vms-editor"
            aria-labelledby="vm-editor-title"
          >
            <div className="vms-panel-heading">
              <div>
                <p className="vms-eyebrow">
                  Machine configuration
                </p>
                <h2 id="vm-editor-title">
                  {editingId
                    ? "Edit virtual machine"
                    : "Create virtual machine"}
                </h2>
              </div>

              {editingId && (
                <span className="vms-badge">
                  Editing
                </span>
              )}
            </div>

            <form onSubmit={saveVM}>
              <fieldset disabled={disabled}>
                <legend className="vms-sr-only">
                  VM details
                </legend>

                <label className="vms-field">
                  <span>Name</span>
                  <input
                    id="vm-name"
                    value={draft.name}
                    maxLength={120}
                    placeholder="Example: Compute VM 1"
                    required
                    onChange={(event) =>
                      setDraft({
                        ...draft,
                        name: event.target.value,
                      })
                    }
                  />
                </label>

                <label className="vms-field">
                  <span>Processing capacity</span>
                  <div className="vms-input-unit">
                    <input
                      id="vm-capacity"
                      type="number"
                      min="0"
                      step="any"
                      required
                      value={
                        draft.capacity_mips
                      }
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          capacity_mips:
                            event.target.value,
                        })
                      }
                    />
                    <b>MIPS</b>
                  </div>
                  <small>
                    500 MIPS processes 1,000 MI
                    in two simulated seconds.
                  </small>
                </label>

                <label className="vms-field">
                  <span>Overload threshold</span>
                  <div className="vms-input-unit">
                    <input
                      id="vm-threshold"
                      type="number"
                      min="0"
                      step="any"
                      required
                      value={
                        draft.overload_threshold
                      }
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          overload_threshold:
                            event.target.value,
                        })
                      }
                    />
                    <b>sec</b>
                  </div>
                  <small>
                    The VM becomes overloaded when
                    queued processing time exceeds
                    this value.
                  </small>
                </label>

                <div className="vms-actions">
                  <button
                    type="submit"
                    className="vms-button primary"
                  >
                    {editingId
                      ? "Save changes"
                      : "Create VM"}
                  </button>

                  {editingId && (
                    <button
                      type="button"
                      className="vms-button secondary"
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
            className="vms-panel vms-library"
            aria-labelledby="vm-list-title"
            aria-busy={disabled}
          >
            <div className="vms-panel-heading">
              <div>
                <p className="vms-eyebrow">
                  Infrastructure library
                </p>
                <h2 id="vm-list-title">
                  Saved machines{" "}
                  <span>{total}</span>
                </h2>
              </div>

              <div className="vms-controls">
                <label htmlFor="vm-page-size">
                  Per page
                </label>
                <select
                  id="vm-page-size"
                  value={limit}
                  disabled={disabled}
                  onChange={(event) => {
                    setLimit(
                      Number(
                        event.target.value
                      )
                    );
                    setPage(1);
                  }}
                >
                  {[5, 10, 20, 50, 100].map(
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
                  className="vms-button secondary"
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
                className="vms-loading"
                role="status"
              >
                <span />
                <p>Loading virtual machines…</p>
              </div>
            ) : vms.length ? (
              <div className="vm-card-grid">
                {vms.map((vm) => (
                  <article
                    className="vm-card"
                    key={vm.id}
                  >
                    <div className="vm-card-heading">
                      <div>
                        <span className="vm-status">
                          Configured
                        </span>
                        <h3>{vm.name}</h3>
                      </div>
                      <span
                        className="vm-indicator"
                        aria-hidden="true"
                      />
                    </div>

                    <dl>
                      <div>
                        <dt>Capacity</dt>
                        <dd>
                          {formatNumber(
                            vm.capacity_mips
                          )}{" "}
                          MIPS
                        </dd>
                      </div>
                      <div>
                        <dt>Overload limit</dt>
                        <dd>
                          {formatNumber(
                            vm.overload_threshold
                          )}{" "}
                          seconds
                        </dd>
                      </div>
                      <div>
                        <dt>VM identifier</dt>
                        <dd title={vm.id}>
                          {vm.id.slice(-10)}
                        </dd>
                      </div>
                    </dl>

                    <div className="vm-capacity-track">
                      <span
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(
                              8,
                              (Number(
                                vm.capacity_mips
                              ) /
                                Math.max(
                                  ...vms.map(
                                    (item) =>
                                      Number(
                                        item.capacity_mips
                                      ) || 0
                                  ),
                                  1
                                )) *
                                100
                            )
                          )}%`,
                        }}
                      />
                    </div>

                    <div className="vms-actions">
                      <button
                        type="button"
                        className="vms-button secondary"
                        disabled={busy}
                        onClick={() => editVM(vm)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="vms-button danger"
                        disabled={busy}
                        onClick={() =>
                          removeVM(vm)
                        }
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="vms-empty">
                <strong>0</strong>
                <h3>No machines configured</h3>
                <p>
                  Create a virtual machine to
                  prepare a simulation.
                </p>
              </div>
            )}

            <nav
              className="vms-pagination"
              aria-label="VM pagination"
            >
              <button
                type="button"
                className="vms-button secondary"
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
                className="vms-button secondary"
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
      </div>
    </main>
  );
}