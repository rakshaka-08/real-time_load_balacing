import api from "./api.js";

const config = (token, signal) => ({
  headers: { Authorization: `Bearer ${token}` }, signal,
});

export async function listSimulations(token, page = 1, signal) {
  const { data } = await api.get("/simulations", {
    ...config(token, signal), params: { page, limit: 10 },
  });
  return data;
}

export async function getSimulation(token, id, signal) {
  const { data } = await api.get(`/simulations/${id}`, config(token, signal));
  return data.simulation;
}

export async function createSimulation(token, taskIds, vmIds) {
  const { data } = await api.post("/simulations", {
    task_ids: taskIds, vm_ids: vmIds, algorithm: "LPT",
    seed: 42, enable_redistribution: true,
  }, config(token));
  return data.simulation;
}

export async function controlSimulation(token, id, action) {
  const { data } = await api.post(`/simulations/${id}/${action}`, {}, config(token));
  return data.simulation;
}
