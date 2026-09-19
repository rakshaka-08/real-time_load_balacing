export default function VMTable({
  vms,
  disabled,
  onEdit,
  onDelete,
}) {
  if (vms.length === 0) {
    return <p>No virtual machines yet. Create one using the form above.</p>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table>
        <caption>Your saved virtual machines</caption>

        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Capacity (MIPS)</th>
            <th scope="col">Overload threshold (seconds)</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>

        <tbody>
          {vms.map((vm) => (
            <tr key={vm.id}>
              <td>{vm.name}</td>
              <td>{vm.capacity_mips.toLocaleString()}</td>
              <td>{vm.overload_threshold.toLocaleString()}</td>
              <td>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onEdit(vm)}
                  aria-label={`Edit ${vm.name}`}
                >
                  Edit
                </button>{" "}
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onDelete(vm)}
                  aria-label={`Delete ${vm.name}`}
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