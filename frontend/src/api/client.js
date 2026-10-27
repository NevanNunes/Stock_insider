import axios from 'axios';

// In development default to http://localhost:8000; in production default to current host (relative URL)
const BASE_URL = import.meta.env.VITE_API_BASE_URL !== undefined
  ? import.meta.env.VITE_API_BASE_URL
  : (import.meta.env.DEV ? 'http://localhost:8000' : '');

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Inject JWT token on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear auth and redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ─────────────────────────────────────────────────
export const authAPI = {
  login: (username, password) =>
    api.post('/api/auth/login', { username, password }),
  register: (payload) =>
    api.post('/api/auth/register', payload),
  me: () => api.get('/api/auth/me'),
};

// ── Reference Data ────────────────────────────────────────
export const symbolsAPI = {
  list: () => api.get('/api/symbols'),
};

export const tradersAPI = {
  list: () => api.get('/api/traders'),
};

// ── Trades ────────────────────────────────────────────────
export const tradesAPI = {
  submit: (payload) => api.post('/api/trades', payload),
  generateSuspicious: () => api.post('/api/trades/generate-suspicious'),
  generateNormal: () => api.post('/api/trades/generate-normal'),
  list: (params = {}) => api.get('/api/trades', { params }),
  get: (id) => api.get(`/api/trades/${id}`),
};

// ── Alerts ────────────────────────────────────────────────
export const alertsAPI = {
  list: (params = {}) => api.get('/api/alerts', { params }),
  latest: () => api.get('/api/alerts/latest'),
  get: (id) => api.get(`/api/alerts/${id}`),
  updateStatus: (id, status) => api.patch(`/api/alerts/${id}/status`, { status }),
};

// ── Investigations ────────────────────────────────────────
export const investigationsAPI = {
  open: (alert_ids, notes) =>
    api.post('/api/investigations', { alert_ids, notes }),
  list: () => api.get('/api/investigations'),
  get: (id) => api.get(`/api/investigations/${id}`),
  update: (id, payload) => api.patch(`/api/investigations/${id}`, payload),
  generateReport: (id) => api.post(`/api/investigations/${id}/report`),
};

// ── Reports ───────────────────────────────────────────────
export const reportsAPI = {
  get: (investigationId) => api.get(`/api/reports/${investigationId}`),
};

// ── Health ────────────────────────────────────────────────
export const healthAPI = {
  check: () => api.get('/api/health'),
};

// ── WebSocket helper ──────────────────────────────────────
export const getWebSocketURL = () => {
  const token = localStorage.getItem('access_token');
  let wsBase;
  if (BASE_URL) {
    wsBase = BASE_URL.replace(/^http/, 'ws');
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    wsBase = `${protocol}//${window.location.host}`;
  }
  return `${wsBase}/api/ws/alerts${token ? `?token=${token}` : ''}`;
};

export default api;
