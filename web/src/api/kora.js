// In development, Vite proxy handles /api -> localhost:4000
// In production, use VITE_API_URL or same-origin
const API_URL = import.meta.env.VITE_API_URL || '';

// Optimizer endpoints
export const getOptimizerStatus = (siteId = 'mahavelona') =>
  fetch(`${API_URL}/api/optimizer/status?siteId=${siteId}`).then(r => r.json());

export const getOptimizerHistory = (siteId = 'mahavelona', limit = 168) =>
  fetch(`${API_URL}/api/optimizer/history?siteId=${siteId}&limit=${limit}`).then(r => r.json());

export const subscribeToOptimizer = (siteId, onMessage, onError) => {
  const es = new EventSource(`${API_URL}/api/optimizer/stream?siteId=${siteId}`);
  es.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch (err) {
      console.error('Failed to parse SSE message:', err);
    }
  };
  es.onerror = (err) => {
    console.error('SSE error:', err);
    if (onError) onError(err);
  };
  return () => es.close();
};

// Forecast endpoints
export const getPVForecast = (siteId = 'mahavelona', hours = 24) =>
  fetch(`${API_URL}/api/forecast/pv?siteId=${siteId}&hours=${hours}`).then(r => r.json());

export const getDemandForecast = (siteId = 'mahavelona', hours = 24) =>
  fetch(`${API_URL}/api/forecast/demand?siteId=${siteId}&hours=${hours}`).then(r => r.json());

export const getRiskAssessment = (siteId = 'mahavelona') =>
  fetch(`${API_URL}/api/forecast/risk?siteId=${siteId}`).then(r => r.json());

export const getForecasts = async (siteId = 'mahavelona', hours = 24) => {
  const [pv, demand, risk] = await Promise.all([
    getPVForecast(siteId, hours),
    getDemandForecast(siteId, hours),
    getRiskAssessment(siteId).catch(() => null),
  ]);
  return { pv, demand, risk };
};

// Simulation control
export const startSimulation = (siteId, options = {}) =>
  fetch(`${API_URL}/api/simulation/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ siteId, ...options })
  }).then(r => r.json());

export const pauseSimulation = (siteId) =>
  fetch(`${API_URL}/api/simulation/pause`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ siteId })
  }).then(r => r.json());

export const resetSimulation = (siteId) =>
  fetch(`${API_URL}/api/simulation/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ siteId })
  }).then(r => r.json());

// Site configuration
export const getSiteConfig = (siteId = 'mahavelona') =>
  fetch(`${API_URL}/api/site/${siteId}`).then(r => r.json());

export const updateSiteConfig = (siteId, config) =>
  fetch(`${API_URL}/api/site/${siteId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  }).then(r => r.json());
