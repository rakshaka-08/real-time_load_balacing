import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import useSimulationSocket from "../hooks/useSimulationSocket.js";
import { listTasks } from "../services/taskService.js";
import { listVMs } from "../services/vmService.js";
import { listSimulations, getSimulation, createSimulation, controlSimulation } from "../services/simulationService.js";
import "./dashboard.css";

const actions = {
  CREATED: ["start", "stop"], RUNNING: ["pause", "stop"],
  PAUSED: ["resume", "stop"], COMPLETED: ["reset"], STOPPED: ["reset"], FAILED: ["reset"],
};
const number = (value) => Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "—";
const message = (error) => error.response?.data?.error || error.response?.data?.msg || "Could not reach the server. Check your connection and retry.";
function Badge({ value }) {
  return <span className={`dash-badge ${String(value).toLowerCase()}`}>{String(value).replaceAll("_", " ")}</span>;
}

function InputPicker({ kind, token, selected, onSelect, onError }) {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [retry, setRetry] = useState(0);
  const tasks = kind === "tasks";
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setResult(null);
    (tasks ? listTasks : listVMs)(token, page, 20, controller.signal)
      .then((data) => { if (!controller.signal.aborted) setResult(data); })
      .catch((error) => { if (!controller.signal.aborted) onError(error); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, page, tasks, retry, onError]);
  return <section className="dash-picker">
    <h3>{tasks ? "Tasks" : "Virtual machines"} <small>{selected.length} selected</small></h3>
    <p className="dash-muted">Choose up to {tasks ? 500 : 100}. Selections stay selected across pages.</p>
    {loading && <p role="status">Loading…</p>}
    {!loading && !result && <button type="button" onClick={() => setRetry(retry + 1)}>Retry loading</button>}
    {result && !result[kind]?.length && <p>No {tasks ? "tasks" : "VMs"} yet. <Link to={tasks ? "/tasks" : "/vms"}>Create some first</Link>.</p>}
    <div className="dash-options">{result?.[kind]?.map((item) => <label key={item.id}>
      <input type="checkbox" checked={selected.includes(item.id)}
        disabled={!selected.includes(item.id) && selected.length >= (tasks ? 500 : 100)}
        onChange={() => onSelect(selected.includes(item.id) ? selected.filter((id) => id !== item.id) : [...selected, item.id])} />
      <span>{item.name}<small>{tasks ? `${number(item.work_mi)} MI · arrives ${number(item.arrival_time)} s` : `${number(item.capacity_mips)} MIPS`}</small></span>
    </label>)}</div>
    <div className="dash-pagination">
      <button type="button" disabled={loading || page === 1} onClick={() => setPage(page - 1)}>Previous</button>
      <span>Page {page} / {Math.max(1, result?.total_pages || 1)}</span>
      <button type="button" disabled={loading || !result || page >= result.total_pages} onClick={() => setPage(page + 1)}>Next</button>
    </div>
  </section>;
}

function NewRun({ token, onCreated, onError }) {
  const [tasks, setTasks] = useState([]);
  const [vms, setVMs] = useState([]);
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    try { onCreated(await createSimulation(token, tasks, vms)); }
    catch (error) { onError(error); }
    finally { setBusy(false); }
  }
  return <form className="dash-panel" onSubmit={submit}>
    <h2>Prepare a simulation</h2>
    <p>Use your saved tasks and machines. This dashboard starts with LPT scheduling, seed 42, and queue redistribution enabled.</p>
    <fieldset disabled={busy}>
      <div className="dash-two">
        <InputPicker kind="tasks" token={token} selected={tasks} onSelect={setTasks} onError={onError} />
        <InputPicker kind="vms" token={token} selected={vms} onSelect={setVMs} onError={onError} />
      </div>
      <button className="dash-primary" disabled={busy || !tasks.length || !vms.length}>{busy ? "Creating…" : "Create simulation"}</button>
    </fieldset>
  </form>;
}

function RunDetail({ token, id, onReset, onError, onChanged }) {
  const [rest, setRest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [refresh, setRefresh] = useState(0);
  const { snapshot, connectionStatus, error, reconnect } = useSimulationSocket(id);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    getSimulation(token, id, controller.signal)
      .then((state) => { if (!controller.signal.aborted) setRest((old) => !old || state.revision >= old.revision ? state : old); })
      .catch((err) => { if (!controller.signal.aborted) onError(err); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, id, refresh, onError]);
  // REST replies can race with newer socket updates. Always render the latest revision.
  const state = snapshot && (!rest || snapshot.revision >= rest.revision) ? snapshot : rest;
  async function control(action) {
    setBusy(action);
    try {
      const next = await controlSimulation(token, id, action);
      if (action === "reset") onReset(next);
      else setRest((old) => !old || next.revision >= old.revision ? next : old);
      onChanged();
    } catch (err) {
      onError(err);
      setRefresh((value) => value + 1);
    } finally { setBusy(""); }
  }
  const connected = connectionStatus === "connected";
  const progress = state?.total_tasks ? Math.round(state.completed_tasks / state.total_tasks * 100) : 0;
  return <section className="dash-panel">
    <div className="dash-heading"><div><p className="dash-eyebrow">Live monitor</p><h2>Simulation {id.slice(-8)}</h2></div><Badge value={connectionStatus} /></div>
    {!connected && <p role="status" className="dash-notice">{error || "Connecting to live updates…"} Displayed data may be stale. <button onClick={reconnect}>Reconnect</button></p>}
    <button disabled={loading || !!busy} onClick={() => setRefresh(refresh + 1)}>Refresh snapshot</button>
    {!state ? <p role="status">{loading ? "Loading simulation…" : "Snapshot unavailable. Retry using Refresh snapshot."}</p> : <>
      <div className="dash-heading dash-run-info"><div><Badge value={state.status} /> <strong>{state.algorithm}</strong><p className="dash-muted">Created {new Date(state.created_at).toLocaleString()}</p></div>
        <div className="dash-controls">{(actions[state.status] || []).map((action) => <button className={action === "stop" ? "dash-danger" : "dash-primary"} key={action}
          disabled={!!busy || !connected} onClick={() => control(action)}>{busy === action ? "Saving…" : action === "reset" ? "Reset as new run" : action[0].toUpperCase() + action.slice(1)}</button>)}</div>
      </div>
      {state.error && <p role="alert" className="dash-alert">{state.error}</p>}
      <div className="dash-stats">
        <div><span>Simulated time</span><strong>{number(state.simulated_time)} <small>s</small></strong></div>
        <div><span>Tasks completed</span><strong>{state.completed_tasks} <small>/ {state.total_tasks}</small></strong></div>
        <div><span>Virtual machines</span><strong>{state.vms.length}</strong></div>
        <div><span>Queue migrations</span><strong>{state.redistribution_count}</strong></div>
      </div>
      <label className="dash-progress">Completion · {progress}%<progress max="100" value={progress} /></label>
      <h3>Machine activity</h3>
      <div className="dash-machines">{state.vms.map((vm) => <article key={vm.id}>
        <div className="dash-heading"><h4>{vm.name}</h4><Badge value={vm.status} /></div>
        <p>{number(vm.capacity_mips)} MIPS</p>
        <dl><dt>Current task</dt><dd>{state.tasks.find((task) => task.id === vm.current_task_id)?.name || "None"}</dd>
          <dt>Queued tasks</dt><dd>{vm.queued_task_ids.length}</dd><dt>Queued work</dt><dd>{number(vm.queued_seconds)} s</dd>
          <dt>Overload threshold</dt><dd>{number(vm.overload_threshold)} s</dd><dt>Busy time</dt><dd>{number(vm.busy_seconds)} s</dd></dl>
      </article>)}</div>
      <h3>Task execution</h3>
      <div className="dash-table-scroll" tabIndex="0" role="region" aria-label="Task execution table"><table><thead><tr><th>Task</th><th>Status</th><th>Machine</th><th>Remaining MI</th><th>Started (s)</th><th>Completed (s)</th></tr></thead>
        <tbody>{state.tasks.map((task) => <tr key={task.id}><td>{task.name}</td><td><Badge value={task.status} /></td><td>{state.vms.find((vm) => vm.id === task.vm_id)?.name || "Unassigned"}</td><td>{number(task.remaining_work_mi)}</td><td>{number(task.started_at)}</td><td>{number(task.completed_at)}</td></tr>)}</tbody></table></div>
      <p className="dash-muted">Queued work excludes the running task. Reset creates a separate run and preserves this one.</p>
    </>}
  </section>;
}


export default function Dashboard() {
  const { user, accessToken, logout } = useAuth();
  const [params, setParams] = useSearchParams();
  const id = params.get("run");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const onError = useCallback((err) => {
    if ([401, 422].includes(err.response?.status)) logout();
    else setError(message(err));
  }, [logout]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listSimulations(accessToken, page, controller.signal)
      .then((data) => { if (!controller.signal.aborted) setResult(data); })
      .catch((err) => { if (!controller.signal.aborted) onError(err); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [accessToken, page, refresh, onError]);
  function select(run) { setError(""); setCreating(false); setParams({ run: run.id }); }
  function created(run) { select(run); setPage(1); setRefresh((value) => value + 1); }
  return <div className="dashboard">
    <header className="dash-top"><Link className="dash-brand" to="/dashboard">LoadLab <span>Simulation workspace</span></Link>
      <nav aria-label="Main navigation"><Link to="/dashboard" aria-current="page">Dashboard</Link><Link to="/tasks">Tasks</Link><Link to="/vms">Virtual machines</Link></nav>
      <button onClick={logout}>Sign out</button></header>
    <main className="dash-main">
      <div className="dash-heading"><div><p className="dash-eyebrow">Distributed systems / Live workspace</p><h1>Simulation dashboard</h1><p className="dash-muted">Watch work move across your machines. Signed in as {user.email}.</p></div>
        <button className="dash-primary" onClick={() => { setError(""); setCreating(!creating); }}>{creating ? "Close setup" : "New simulation"}</button></div>
      {error && <div role="alert" className="dash-alert">{error} <button onClick={() => setError("")}>Dismiss</button></div>}
      {creating && <NewRun token={accessToken} onCreated={created} onError={onError} />}
      <div className="dash-layout"><aside className="dash-panel">
        <div className="dash-heading"><h2>Saved runs</h2><button disabled={loading} onClick={() => setRefresh(refresh + 1)}>Refresh</button></div>
        <p className="dash-muted">Select a run to monitor it live. Refresh this list for updated summaries.</p>
        {loading ? <p role="status">Loading runs…</p> : result?.simulations.length ? result.simulations.map((run) => <button key={run.id} className={`dash-run ${id === run.id ? "selected" : ""}`} aria-pressed={id === run.id} onClick={() => select(run)}>
          <strong>{run.algorithm} · {run.id.slice(-8)}</strong><Badge value={run.status} /><small>{new Date(run.created_at).toLocaleString()}</small></button>) : <p>No runs to display. Create a simulation to begin.</p>}
        <div className="dash-pagination"><button disabled={loading || page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>{page} / {Math.max(1, result?.total_pages || 1)}</span><button disabled={loading || !result || page >= result.total_pages} onClick={() => setPage(page + 1)}>Next</button></div>
      </aside>
        {id ? <RunDetail key={id} token={accessToken} id={id} onReset={created} onError={onError} onChanged={() => setRefresh((value) => value + 1)} /> : <section className="dash-panel dash-empty"><span className="dash-empty-icon">◫</span><h2>Your next run starts here</h2><p>Select a saved simulation or create one using your tasks and virtual machines.</p><button className="dash-primary" onClick={() => setCreating(true)}>Prepare a simulation</button></section>}
      </div>
    </main>
  </div>;
}
