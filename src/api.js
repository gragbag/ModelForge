// Tiny API client for the ModelForge backend.
// Stores the JWT in localStorage and attaches it to every request.

const BASE = "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("token");
}
export function setToken(token) {
  localStorage.setItem("token", token);
}
export function clearToken() {
  localStorage.removeItem("token");
}

// Core request helper: adds the Authorization header + JSON handling, and
// throws an Error with the API's detail message on failure.
async function request(path, { method = "GET", body, isForm = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isForm) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  // Some endpoints return no body.
  return res.status === 204 ? null : res.json();
}

// --- Auth ---
export const register = (email, password) =>
  request("/auth/register", { method: "POST", body: { email, password } });
export const login = (email, password) =>
  request("/auth/login", { method: "POST", body: { email, password } });
export const getMe = () => request("/auth/me");

// --- Datasets ---
export const listDatasets = () => request("/datasets");
export function uploadDataset(file) {
  const form = new FormData();
  form.append("file", file);
  return request("/datasets", { method: "POST", body: form, isForm: true });
}
export const deleteDataset = (id) =>
  request(`/datasets/${id}`, { method: "DELETE" });
export const getDatasetPreview = (id) => request(`/datasets/${id}/preview`);

// --- Jobs ---
export const listJobs = () => request("/jobs");
export const listModelTypes = () => request("/jobs/model-types");
export const createJob = (payload) =>
  request("/jobs", { method: "POST", body: payload });
export const getJob = (id) => request(`/jobs/${id}`);
export const deleteJob = (id) => request(`/jobs/${id}`, { method: "DELETE" });

// --- Deployments + prediction ---
export const listDeployments = () => request("/deployments");
export const listModelVersions = () => request("/deployments/available-models");
export const createDeployment = (payload) =>
  request("/deployments", { method: "POST", body: payload });
export const deleteDeployment = (id) =>
  request(`/deployments/${id}`, { method: "DELETE" });
export const predict = (deploymentId, rows) =>
  request(`/deployments/${deploymentId}/predict`, {
    method: "POST",
    body: { rows },
  });
export function predictCsv(deploymentId, file) {
  const form = new FormData();
  form.append("file", file);
  return request(`/deployments/${deploymentId}/predict-csv`, {
    method: "POST",
    body: form,
    isForm: true,
  });
}
