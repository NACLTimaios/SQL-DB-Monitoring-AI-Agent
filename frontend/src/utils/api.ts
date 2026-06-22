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

// Clear the session and send the user back to the Sign In page. Works even on
// the dashboard route ("/") by notifying the React app via a custom event, so a
// timed-out session doesn't sit silently on a stale screen. An optional reason is
// stashed for the login page to display.
export function forceSignOut(reason?: string) {
  if (reason) sessionStorage.setItem('signout_reason', reason);
  localStorage.removeItem('access_token');
  window.dispatchEvent(new CustomEvent('app:signout'));
}

// Response interceptor: on 401 (expired/invalid token) for an authenticated
// session, sign out and show the login page. Skipped when there was no token
// (e.g. a failed login attempt) so the login form can show its own error.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && localStorage.getItem('access_token')) {
      forceSignOut('Your session has expired. Please sign in again.');
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
  forceSignOut();
}
