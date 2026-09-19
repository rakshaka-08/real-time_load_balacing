import api from "./api.js";

function authorization(token) {
  return { Authorization: `Bearer ${token}` };
}

export async function listVMs(token, page = 1, limit = 20, signal) {
  const response = await api.get("/vms", {
    headers: authorization(token),
    params: { page, limit },
    signal,
  });
  return response.data;
}

export async function createVM(token, vm) {
  const response = await api.post("/vms", vm, {
    headers: authorization(token),
  });
  return response.data.vm;
}

export async function updateVM(token, id, changes) {
  const response = await api.patch(`/vms/${id}`, changes, {
    headers: authorization(token),
  });
  return response.data.vm;
}

export async function deleteVM(token, id) {
  await api.delete(`/vms/${id}`, {
    headers: authorization(token),
  });
}