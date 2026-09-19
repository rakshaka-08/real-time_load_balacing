import api from "./api.js";

function authorization(token) {
  return { Authorization: `Bearer ${token}` };
}

export async function listTasks(token, page = 1, limit = 20, signal) {
  const response = await api.get("/tasks", {
    headers: authorization(token),
    params: { page, limit },
    signal,
  });
  return response.data;
}

export async function createTask(token, task) {
  const response = await api.post("/tasks", task, {
    headers: authorization(token),
  });
  return response.data.task;
}

export async function updateTask(token, id, changes) {
  const response = await api.patch(`/tasks/${id}`, changes, {
    headers: authorization(token),
  });
  return response.data.task;
}

export async function deleteTask(token, id) {
  await api.delete(`/tasks/${id}`, {
    headers: authorization(token),
  });
}

export async function generateTasks(token, settings) {
  const response = await api.post("/tasks/generate", settings, {
    headers: authorization(token),
  });
  return response.data;
}