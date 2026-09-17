import api from "./api.js";

export async function registerUser(email, password) {
  const response = await api.post("/auth/register", {
    email,
    password,
  });

  return response.data;
}

export async function loginUser(email, password) {
  const response = await api.post("/auth/login", {
    email,
    password,
  });

  return response.data;
}

export async function fetchCurrentUser(accessToken) {
  const response = await api.get("/auth/me", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return response.data.user;
}