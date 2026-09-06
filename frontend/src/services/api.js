/**
 * NeerNetra -- API Service
 * ==========================
 * One client function per backend endpoint. Every export here is
 * called from at least one screen in the app -- see AGENT_CONTEXT.md
 * for the full endpoint list this mirrors.
 */

import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

/** Flood Risk */
export const riskAPI = {
  getCurrentRisk: (lat, lon) =>
    api.get('/api/risk', { params: { lat, lon } }),
  getRiskMap: () =>
    api.get('/api/risk-map'),
};

/** Weather & Rainfall */
export const weatherAPI = {
  getRainfall: (lat, lon) =>
    api.get('/api/rainfall/current', { params: { lat, lon } }),
  getForecast: (lat, lon, hours = 48) =>
    api.get('/api/weather/forecast', { params: { lat, lon, hours } }),
};

/** Historical Flood Events */
export const floodEventsAPI = {
  getEvents: () => api.get('/api/flood-events'),
};

/** Flood Dynamics: propagation, arrival time, cascade, infrastructure, LSET */
export const dynamicsAPI = {
  getPropagation: (origin, probability = 0.8, rainfall_intensity = 1.0) =>
    api.get('/api/propagation', { params: { origin, probability, rainfall_intensity } }),
  getArrivalTime: (origin, target, probability = 0.8, rainfall_intensity = 1.0) =>
    api.get('/api/arrival-time', { params: { origin, target, probability, rainfall_intensity } }),
  getAllArrivals: (origin, probability = 0.8, rainfall_intensity = 1.0) =>
    api.get('/api/arrival-time/all', { params: { origin, probability, rainfall_intensity } }),
  getCascade: (location, rain_6h = 0, rain_24h = 0) =>
    api.get('/api/cascade', { params: { location, rain_6h, rain_24h } }),
  getInfrastructureRisk: (origin = 'Kedarnath', probability = 0.8, rainfall_intensity = 1.0) =>
    api.get('/api/infrastructure/risk', { params: { origin, probability, rainfall_intensity } }),
  getLSET: (origin, target, probability = 0.8, rainfall_intensity = 1.0) =>
    api.get('/api/lset', { params: { origin, target, probability, rainfall_intensity } }),
  getAllLSET: (origin, probability = 0.8, rainfall_intensity = 1.0) =>
    api.get('/api/lset/all', { params: { origin, probability, rainfall_intensity } }),
};

/** System / Metadata */
export const systemAPI = {
  healthCheck: () => api.get('/health'),
  getLocations: () => api.get('/api/locations'),
};

/** Demo Replay -- Kedarnath 2013 disaster, time-stepped */
export const demoAPI = {
  start: () => api.post('/api/demo/start'),
  stop: () => api.post('/api/demo/stop'),
  advance: () => api.post('/api/demo/advance'),
  goToStep: (step) => api.post(`/api/demo/step/${step}`),
  getState: () => api.get('/api/demo/state'),
  getScenario: () => api.get('/api/demo/scenario'),
};

export default api;
