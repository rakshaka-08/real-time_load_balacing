export default function TaskTable({
  tasks,
  disabled,
  onEdit,
  onDelete,
}) {
  if (tasks.length === 0) {
    return <p>No tasks yet. Create a task or generate a workload.</p>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table>
        <caption>Your saved tasks</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Work (MI)</th>
            <th scope="col">Arrival (seconds)</th>
            <th scope="col">Created</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>

        <tbody>
          {tasks.map((task) => (
            <tr key={task.id}>
              <td>{task.name}</td>
              <td>{task.work_mi.toLocaleString()}</td>
              <td>{task.arrival_time.toLocaleString()}</td>
              <td>{new Date(task.created_at).toLocaleString()}</td>
              <td>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onEdit(task)}
                  aria-label={`Edit ${task.name}`}
                >
                  Edit
                </button>{" "}
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onDelete(task)}
                  aria-label={`Delete ${task.name}`}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}