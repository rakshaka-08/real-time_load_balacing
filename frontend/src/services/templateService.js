import api from "./api.js";

function requestConfig(token, signal) {
  return {
    signal,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };
}

export async function listTemplates(token, signal) {
  const response = await api.get(
    "/templates",
    requestConfig(token, signal)
  );

  return response.data;
}

export async function createTemplate(token, payload) {
  const response = await api.post(
    "/templates",
    payload,
    requestConfig(token)
  );

  return response.data.template;
}

export async function renameTemplate(token, templateId, name) {
  const response = await api.put(
    `/templates/${templateId}`,
    { name },
    requestConfig(token)
  );

  return response.data.template;
}

export async function deleteTemplate(token, templateId) {
  await api.delete(
    `/templates/${templateId}`,
    requestConfig(token)
  );
}