import api from "./api.js";

function config(token, signal) {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    signal,
  };
}

export async function listSimulations(
  token,
  page = 1,
  signal
) {
  const response = await api.get(
    "/simulations",
    {
      ...config(token, signal),
      params: {
        page,
        limit: 10,
      },
    }
  );

  return response.data;
}

export async function getSimulation(
  token,
  id,
  signal
) {
  const response = await api.get(
    `/simulations/${id}`,
    config(token, signal)
  );

  return response.data.simulation;
}

export async function createSimulation(
  token,
  taskIds,
  vmIds,
  algorithm,
  parameters,
  seed,
  enableRedistribution
) {
  const response = await api.post(
    "/simulations",
    {
      task_ids: taskIds,
      vm_ids: vmIds,
      algorithm,
      parameters,
      seed,
      enable_redistribution:
        enableRedistribution,
    },
    config(token)
  );

  return response.data.simulation;
}

export async function controlSimulation(
  token,
  id,
  action
) {
  const response = await api.post(
    `/simulations/${id}/${action}`,
    {},
    config(token)
  );

  return response.data.simulation;
}

export async function benchmarkAlgorithms(
  token,
  {
    taskIds,
    vmIds,
    seed = 42,
    parameters = {},
    enableRedistribution = true,
  },
  signal
) {
  const response = await api.post(
    "/simulations/benchmark",
    {
      task_ids: taskIds,
      vm_ids: vmIds,
      seed,
      parameters,
      enable_redistribution:
        enableRedistribution,
    },
    config(token, signal)
  );

  return response.data;
}