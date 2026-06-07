import axios from 'axios';

const API_BASE = '/api';

const getAuthHeader = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export async function fetchHealth() {
  try {
    const response = await axios.get(`${API_BASE}/health`);
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    return null;
  }
}

export async function fetchAgentStatus() {
  try {
    const response = await axios.get(`${API_BASE}/agent-status`, {
      headers: getAuthHeader(),
    });
    return response.data;
  } catch (error) {
    console.error('Agent status failed:', error);
    return null;
  }
}

export async function fetchDatabaseSummary(dbId: number) {
  try {
    const response = await axios.get(`${API_BASE}/database/${dbId}/summary`, {
      headers: getAuthHeader(),
    });
    return response.data;
  } catch (error) {
    console.error('Database summary failed:', error);
    return null;
  }
}

export async function fetchInsightsPending() {
  try {
    const response = await axios.get(`${API_BASE}/insights/pending`, {
      headers: getAuthHeader(),
    });
    return response.data;
  } catch (error) {
    console.error('Insights pending failed:', error);
    return null;
  }
}

export async function fetchActivity(limit: number) {
  try {
    const response = await axios.get(`${API_BASE}/activity?limit=${limit}`, {
      headers: getAuthHeader(),
    });
    return response.data;
  } catch (error) {
    console.error('Activity fetch failed:', error);
    return [];
  }
}

export function logout() {
  localStorage.removeItem('token');
  window.location.href = '/';
}
