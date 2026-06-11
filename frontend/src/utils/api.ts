import axios from 'axios';

const API_BASE = '/api';

// Centralized axios instance with auth + 401 handling
const client = axios.create({ baseURL: API_BASE });

// Request interceptor: attach JWT from localStorage to every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: on 401 (expired/invalid token), clear session and
// redirect to login instead of leaving the UI in a silent broken state.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('access_token');
      // Avoid redirect loops if already on the login screen
      if (window.location.pathname !== '/') {
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  }
);

export { client };

export async function fetchHealth() {
  try {
    const response = await client.get('/health');
    return response.data;
  } catch {
    return null;
  }
}

export async function fetchAgentStatus() {
  try {
    const response = await client.get('/agent-status');
    return response.data;
  } catch {
    return null;
  }
}

export async function fetchDatabaseSummary(dbId: number) {
  try {
    const response = await client.get(`/database/${dbId}/summary`);
    return response.data;
  } catch {
    return null;
  }
}

export async function fetchInsightsPending() {
  try {
    const response = await client.get('/insights/pending');
    return response.data;
  } catch {
    return null;
  }
}

export async function fetchActivity(limit: number) {
  try {
    const response = await client.get(`/activity?limit=${limit}`);
    return response.data;
  } catch {
    return [];
  }
}

export function logout() {
  localStorage.removeItem('access_token');
  window.location.href = '/';
}
