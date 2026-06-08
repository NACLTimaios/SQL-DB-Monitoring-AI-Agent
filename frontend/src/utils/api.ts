import axios from 'axios';

const API_BASE = '/api';

const getAuthHeader = () => {
  const token = localStorage.getItem('access_token');
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  console.log('Auth header:', headers ? 'Token present' : 'No token');
  return headers;
};

export async function fetchHealth() {
  try {
    console.log('Fetching health...');
    const response = await axios.get(`${API_BASE}/health`);
    console.log('Health response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Health check failed:', error?.response?.data || error.message);
    return null;
  }
}

export async function fetchAgentStatus() {
  try {
    console.log('Fetching agent status...');
    const response = await axios.get(`${API_BASE}/agent-status`, {
      headers: getAuthHeader(),
    });
    console.log('Agent status response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Agent status failed:', error?.response?.data || error.message);
    return null;
  }
}

export async function fetchDatabaseSummary(dbId: number) {
  try {
    console.log('Fetching database summary...');
    const response = await axios.get(`${API_BASE}/database/${dbId}/summary`, {
      headers: getAuthHeader(),
    });
    console.log('Database summary response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Database summary failed:', error?.response?.data || error.message);
    return null;
  }
}

export async function fetchInsightsPending() {
  try {
    console.log('Fetching insights pending...');
    const response = await axios.get(`${API_BASE}/insights/pending`, {
      headers: getAuthHeader(),
    });
    console.log('Insights pending response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Insights pending failed:', error?.response?.data || error.message);
    return null;
  }
}

export async function fetchActivity(limit: number) {
  try {
    console.log('Fetching activity...');
    const response = await axios.get(`${API_BASE}/activity?limit=${limit}`, {
      headers: getAuthHeader(),
    });
    console.log('Activity response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Activity fetch failed:', error?.response?.data || error.message);
    return [];
  }
}

export function logout() {
  localStorage.removeItem('access_token');
  window.location.href = '/';
}
