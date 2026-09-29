import api from "./api.js";

export async function getSystemHealth(signal) {
  try {
    const response = await api.get("/health/status", {
      signal,
    });

    return response.data;
  } catch (error) {
    if (error.response?.data) {
      return error.response.data;
    }

    throw error;
  }
}