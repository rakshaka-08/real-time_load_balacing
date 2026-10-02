import {
    useEffect,
    useMemo,
    useState,
  } from "react";
  
  import { useAuth } from "../context/AuthContext.jsx";
  import {
    benchmarkAlgorithms,
  } from "../services/simulationService.js";
  import {
    listTasks,
  } from "../services/taskService.js";
  import {
    listVMs,
  } from "../services/vmService.js";
  
  import "./algorithm-benchmark.css";
  
  const METRICS = [
    {
      key: "system_utilization",
      label: "System utilization",
      unit: "%",
    },
    {
      key: "total_response_time",
      label: "Total response time",
      unit: "s",
    },
    {
      key: "average_response_time",
      label: "Average response time",
      unit: "s",
    },
    {
      key: "makespan",
      label: "Makespan",
      unit: "s",
    },
    {
      key: "load_imbalance",
      label: "Load imbalance",
      unit: "",
    },
    {
      key: "scheduler_execution_seconds",
      label: "Scheduler execution",
      unit: "s",
    },
    {
      key: "redistribution_count",
      label: "Redistributions",
      unit: "",
    },
  ];
  
  const ALGORITHM_NAMES = {
    GA: "GA",
    HBA: "HBA",
    GA_HBA: "GA + HBA",
    LPT: "LPT",
    SPT: "SPT",
  };
  
  function number(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed)
      ? parsed
      : 0;
  }
  
  function format(value, unit) {
    const formatted = number(
      value
    ).toLocaleString(undefined, {
      maximumFractionDigits: 5,
    });
  
    return unit
      ? `${formatted} ${unit}`
      : formatted;
  }
  
  function message(error) {
    return (
      error.response?.data?.error ||
      error.response?.data?.msg ||
      "Benchmark request failed."
    );
  }
  
  function SelectionList({
    title,
    items,
    selected,
    onChange,
    detail,
  }) {
    function toggle(id) {
      onChange(
        selected.includes(id)
          ? selected.filter(
              (value) => value !== id
            )
          : [...selected, id]
      );
    }
  
    return (
      <section className="benchmark-selection">
        <div>
          <h3>{title}</h3>
          <span>
            {selected.length} selected
          </span>
        </div>
  
        <div className="benchmark-options">
          {items.map((item) => (
            <label key={item.id}>
              <input
                type="checkbox"
                checked={selected.includes(
                  item.id
                )}
                onChange={() =>
                  toggle(item.id)
                }
              />
              <span>
                <strong>{item.name}</strong>
                <small>{detail(item)}</small>
              </span>
            </label>
          ))}
        </div>
      </section>
    );
  }
  
  export default function AlgorithmBenchmark() {
    const {
      accessToken,
      logout,
    } = useAuth();
  
    const [tasks, setTasks] = useState([]);
    const [vms, setVMs] = useState([]);
    const [
      selectedTasks,
      setSelectedTasks,
    ] = useState([]);
    const [
      selectedVMs,
      setSelectedVMs,
    ] = useState([]);
    const [seed, setSeed] = useState("42");
    const [
      redistribution,
      setRedistribution,
    ] = useState(true);
    const [
      loadingInputs,
      setLoadingInputs,
    ] = useState(true);
    const [
      benchmarking,
      setBenchmarking,
    ] = useState(false);
    const [error, setError] = useState("");
    const [result, setResult] = (
      useState(null)
    );
  
    useEffect(() => {
      const controller =
        new AbortController();
  
      async function load() {
        setLoadingInputs(true);
        setError("");
  
        try {
          const [
            taskResult,
            vmResult,
          ] = await Promise.all([
            listTasks(
              accessToken,
              1,
              100,
              controller.signal
            ),
            listVMs(
              accessToken,
              1,
              100,
              controller.signal
            ),
          ]);
  
          if (
            controller.signal.aborted
          ) {
            return;
          }
  
          const loadedTasks =
            taskResult.tasks || [];
          const loadedVMs =
            vmResult.vms || [];
  
          setTasks(loadedTasks);
          setVMs(loadedVMs);
  
          setSelectedTasks(
            loadedTasks
              .slice(0, 10)
              .map((task) => task.id)
          );
  
          setSelectedVMs(
            loadedVMs
              .slice(0, 3)
              .map((vm) => vm.id)
          );
        } catch (requestError) {
          if (
            controller.signal.aborted
          ) {
            return;
          }
  
          if (
            [401, 422].includes(
              requestError.response?.status
            )
          ) {
            logout();
            return;
          }
  
          setError(
            message(requestError)
          );
        } finally {
          if (
            !controller.signal.aborted
          ) {
            setLoadingInputs(false);
          }
        }
      }
  
      load();
  
      return () =>
        controller.abort();
    }, [accessToken, logout]);
  
    async function runBenchmark(event) {
      event.preventDefault();
  
      const numericSeed = Number(seed);
  
      if (
        !Number.isInteger(numericSeed) ||
        numericSeed < 0 ||
        numericSeed > 4294967295
      ) {
        setError(
          "Seed must be a whole number between 0 and 4294967295."
        );
        return;
      }
  
      if (
        !selectedTasks.length ||
        !selectedVMs.length
      ) {
        setError(
          "Select at least one task and one virtual machine."
        );
        return;
      }
  
      setBenchmarking(true);
      setError("");
      setResult(null);
  
      try {
        const response =
          await benchmarkAlgorithms(
            accessToken,
            {
              taskIds: selectedTasks,
              vmIds: selectedVMs,
              seed: numericSeed,
              enableRedistribution:
                redistribution,
              parameters: {},
            }
          );
  
        setResult(response.benchmark);
      } catch (requestError) {
        if (
          [401, 422].includes(
            requestError.response?.status
          )
        ) {
          logout();
          return;
        }
  
        setError(message(requestError));
      } finally {
        setBenchmarking(false);
      }
    }
  
    const rows =
      result?.algorithms || [];
  
    const chartData = useMemo(
      () =>
        METRICS.map((metric) => {
          const values = rows.map(
            (row) =>
              number(row[metric.key])
          );
  
          return {
            ...metric,
            maximum: Math.max(
              ...values,
              0.000001
            ),
            values: rows.map(
              (row) => ({
                algorithm:
                  ALGORITHM_NAMES[
                    row.algorithm
                  ] || row.algorithm,
                value: number(
                  row[metric.key]
                ),
              })
            ),
          };
        }),
      [rows]
    );
  
    return (
      <section className="benchmark-panel">
        <div className="benchmark-heading">
          <div>
            <p>
              Controlled experiment
            </p>
            <h2>
              Five-algorithm benchmark
            </h2>
            <span>
              Every algorithm receives the
              same tasks, VMs, seed, and
              redistribution setting.
            </span>
          </div>
  
          {result && (
            <strong>
              Seed {result.seed} ·{" "}
              {result.task_count} tasks ·{" "}
              {result.vm_count} VMs
            </strong>
          )}
        </div>
  
        {error && (
          <div
            className="benchmark-error"
            role="alert"
          >
            {error}
          </div>
        )}
  
        {loadingInputs ? (
          <p role="status">
            Loading benchmark inputs…
          </p>
        ) : (
          <form onSubmit={runBenchmark}>
            <div className="benchmark-input-grid">
              <SelectionList
                title="Tasks"
                items={tasks}
                selected={
                  selectedTasks
                }
                onChange={
                  setSelectedTasks
                }
                detail={(task) =>
                  `${format(
                    task.work_mi,
                    "MI"
                  )} · arrives ${format(
                    task.arrival_time,
                    "s"
                  )}`
                }
              />
  
              <SelectionList
                title="Virtual machines"
                items={vms}
                selected={selectedVMs}
                onChange={setSelectedVMs}
                detail={(vm) =>
                  format(
                    vm.capacity_mips,
                    "MIPS"
                  )
                }
              />
            </div>
  
            <div className="benchmark-controls">
              <label>
                <span>Random seed</span>
                <input
                  type="number"
                  min="0"
                  max="4294967295"
                  step="1"
                  value={seed}
                  onChange={(event) =>
                    setSeed(
                      event.target.value
                    )
                  }
                />
              </label>
  
              <label className="benchmark-switch">
                <input
                  type="checkbox"
                  checked={redistribution}
                  onChange={(event) =>
                    setRedistribution(
                      event.target.checked
                    )
                  }
                />
                <span>
                  Enable redistribution
                </span>
              </label>
  
              <button
                type="submit"
                disabled={
                  benchmarking ||
                  !selectedTasks.length ||
                  !selectedVMs.length
                }
              >
                {benchmarking
                  ? "Running five algorithms…"
                  : "Run fair benchmark"}
              </button>
            </div>
          </form>
        )}
  
        {rows.length > 0 && (
          <>
            <div className="benchmark-charts">
              {chartData.map((metric) => (
                <article
                  className="benchmark-chart"
                  key={metric.key}
                >
                  <div>
                    <h3>{metric.label}</h3>
                    <small>
                      Measured from completed
                      simulation runs
                    </small>
                  </div>
  
                  <div className="benchmark-bars">
                    {metric.values.map(
                      (entry) => (
                        <div
                          className="benchmark-bar"
                          key={
                            entry.algorithm
                          }
                        >
                          <span>
                            {entry.algorithm}
                          </span>
  
                          <div>
                            <i
                              style={{
                                width: `${Math.max(
                                  2,
                                  (entry.value /
                                    metric.maximum) *
                                    100
                                )}%`,
                              }}
                            />
                          </div>
  
                          <strong>
                            {format(
                              entry.value,
                              metric.unit
                            )}
                          </strong>
                        </div>
                      )
                    )}
                  </div>
                </article>
              ))}
            </div>
  
            <div
              className="benchmark-table-scroll"
              role="region"
              tabIndex="0"
              aria-label="Algorithm comparison table"
            >
              <table>
                <thead>
                  <tr>
                    <th>Algorithm</th>
                    {METRICS.map(
                      (metric) => (
                        <th key={metric.key}>
                          {metric.label}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
  
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.algorithm}>
                      <th>
                        {ALGORITHM_NAMES[
                          row.algorithm
                        ] || row.algorithm}
                      </th>
  
                      {METRICS.map(
                        (metric) => (
                          <td key={metric.key}>
                            {format(
                              row[metric.key],
                              metric.unit
                            )}
                          </td>
                        )
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
  
            <p className="benchmark-note">
              These results describe only the
              selected workload and configuration.
              They do not establish one algorithm
              as universally superior.
            </p>
          </>
        )}
      </section>
    );
  }