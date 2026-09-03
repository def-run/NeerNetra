/**
 * NeerNetra -- Shared constants & formatting helpers
 * =====================================================
 * Single source of truth for risk colors, urgency colors, and the
 * small formatting utilities used throughout the dashboard.
 */

export const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

export const RISK_COLORS = {
  LOW: '#5fbf77',
  MEDIUM: '#e0a83e',
  HIGH: '#e2622d',
  CRITICAL: '#c4262e',
};

export const RISK_BG = {
  LOW: 'rgba(95, 191, 119, 0.13)',
  MEDIUM: 'rgba(224, 168, 62, 0.13)',
  HIGH: 'rgba(226, 98, 45, 0.13)',
  CRITICAL: 'rgba(196, 38, 46, 0.15)',
};

export const URGENCY_COLORS = {
  EXPIRED: '#c4262e',
  EVACUATE_NOW: '#e2622d',
  PREPARE_EVACUATION: '#e0a83e',
  ALERT: '#d6b154',
  MONITOR: '#5fbf77',
};

export const URGENCY_LABELS = {
  EXPIRED: 'Expired',
  EVACUATE_NOW: 'Evacuate now',
  PREPARE_EVACUATION: 'Prepare evacuation',
  ALERT: 'Alert',
  MONITOR: 'Monitor',
};

export const CONFIDENCE_COLORS = {
  HIGH: '#5fbf77',
  MEDIUM: '#e0a83e',
  LOW: '#e2622d',
  VERY_LOW: '#c4262e',
};

/** Ordered, upstream -> downstream. Mirrors backend PILOT_NETWORK. */
export const PILOT_ORIGINS = [
  'Kedarnath', 'Gaurikund', 'Sonprayag', 'Rampur',
  'Phata', 'Guptkashi', 'Kalimath', 'Agastmuni', 'Rudraprayag',
];

export function riskColor(level) {
  return RISK_COLORS[level] || RISK_COLORS.LOW;
}

export function urgencyColor(urgency) {
  return URGENCY_COLORS[urgency] || '#62766d';
}

export function formatMinutes(min) {
  if (min == null) return '--';
  if (min <= 0) return 'now';
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function formatPct(v, digits = 0) {
  if (v == null) return '--';
  return `${(v * 100).toFixed(digits)}%`;
}

export function formatMm(v) {
  if (v == null) return '--';
  return `${Number(v).toFixed(1)} mm`;
}

export function formatClock(iso) {
  if (!iso) return '--';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '--';
  }
}

export function formatDate(iso) {
  if (!iso) return '--';
  try {
    return new Date(iso).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return iso;
  }
}

export function titleCase(str) {
  if (!str) return '';
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
