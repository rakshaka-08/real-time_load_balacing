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
export async function listSharedTemplates(token, signal) {
    const response = await api.get(
      "/templates/shared",
      requestConfig(token, signal)
    );
  
    return response.data;
  }
  
  export async function shareTemplate(token, templateId, email) {
    const response = await api.post(
      `/templates/${templateId}/share`,
      { email },
      requestConfig(token)
    );
  
    return response.data.template;
  }
  
  export async function revokeTemplateAccess(
    token,
    templateId,
    collaboratorId
  ) {
    await api.delete(
      `/templates/${templateId}/collaborators/${collaboratorId}`,
      requestConfig(token)
    );
  }