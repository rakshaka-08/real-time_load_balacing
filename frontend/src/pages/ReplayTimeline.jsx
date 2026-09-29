import { useEffect, useState } from "react";

import { formatReplayTime } from "../services/replayService.js";

function Badge({ value }) {
  return (
    <span className={`replay-badge ${String(value).toLowerCase()}`}>
      {value}
    </span>
  );
}

export default function ReplayTimeline({
  frame,
  endTime,
  onTimeChange,
}) {
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return undefined;

    const interval = window.setInterval(() => {
      onTimeChange((current) => {
        const next = Math.min(current + Math.max(endTime / 100, 0.1), endTime);

        if (next >= endTime) {
          setPlaying(false);
        }

        return next;
      });
    }, 250);

    return () => window.clearInterval(interval);
  }, [playing, endTime, onTimeChange]);

  return (
    <section className="replay-panel">
      <div className="replay-heading">
        <div>
          <p className="replay-eyebrow">EXECUTION TIMELINE</p>
          <h2>Simulated time: {formatReplayTime(frame.time)} s</h2>
        </div>

        <div className="replay-controls">
          <button
            type="button"
            onClick={() => onTimeChange(0)}
            disabled={frame.time === 0}
          >
            Reset
          </button>

          <button
            type="button"
            className="replay-primary"
            onClick={() => setPlaying((current) => !current)}
            disabled={frame.time >= endTime}
          >
            {playing ? "Pause" : "Play"}
          </button>
        </div>
      </div>

      <input
        className="replay-slider"
        type="range"
        min="0"
        max={endTime || 1}
        step={Math.max(endTime / 200, 0.01)}
        value={frame.time}
        onChange={(event) => {
          setPlaying(false);
          onTimeChange(Number(event.target.value));
        }}
      />

      <div className="replay-counts">
        <span>Waiting: {frame.waiting_tasks}</span>
        <span>Running: {frame.running_tasks}</span>
        <span>Completed: {frame.completed_tasks}</span>
      </div>

      <div className="replay-table-scroll">
        <table>
          <thead>
            <tr>
              <th>Task</th>
              <th>State at this time</th>
              <th>Started (s)</th>
              <th>Completed (s)</th>
            </tr>
          </thead>

          <tbody>
            {frame.tasks.map((task) => (
              <tr key={task.id}>
                <td>{task.name}</td>
                <td>
                  <Badge value={task.replay_status} />
                </td>
                <td>{formatReplayTime(task.started_at)}</td>
                <td>{formatReplayTime(task.completed_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}