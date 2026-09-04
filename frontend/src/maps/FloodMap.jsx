/**
 * NeerNetra -- FloodMap
 * =======================
 * Interactive Leaflet map with risk-colored pilot markers, propagation
 * path lines, an optional historical-event layer, and click-anywhere
 * risk querying (GET /api/risk for the exact clicked coordinate).
 */

import { useMemo } from 'react';
import {
  MapContainer, TileLayer, CircleMarker, Polyline, Popup, Tooltip, useMapEvents,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { riskColor, formatPct, formatMm } from '../utils/constants';

const PILOT_CENTER = [30.55, 79.04];
const DEFAULT_ZOOM = 10;

const RISK_RADIUS = { LOW: 7, MEDIUM: 9, HIGH: 12, CRITICAL: 15 };

/** River path approximation for the Mandakini corridor */
const RIVER_PATH = [
  [30.7346, 79.0669],
  [30.6560, 79.0900],
  [30.6280, 79.0700],
  [30.5700, 79.0600],
  [30.5300, 79.0700],
  [30.5260, 79.0260],
  [30.2840, 78.9800],
];

function ClickCatcher({ onMapClick }) {
  useMapEvents({
    click(e) {
      if (onMapClick) onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

function FloodMap({
  locations,
  selectedLocation,
  onLocationSelect,
  propagation,
  onMapClick,
  queryPoint,
  historicalEvents,
  center,
  zoom,
}) {
  const locData = locations || [];

  const propagationPath = useMemo(() => {
    if (!propagation?.time_steps) return null;
    return propagation.time_steps
      .flatMap((s) => s.affected_locations || [])
      .filter((v, i, a) => a.findIndex((x) => x.name === v.name) === i)
      .map((l) => [l.lat, l.lon]);
  }, [propagation]);

  return (
    <MapContainer
      center={center || PILOT_CENTER}
      zoom={zoom || DEFAULT_ZOOM}
      style={{ height: '100%', width: '100%', minHeight: '400px' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key=cb1_2qer_1_ae4b94f6df897e006d13c802"
      />

      {onMapClick && <ClickCatcher onMapClick={onMapClick} />}

      <Polyline
        positions={RIVER_PATH}
        pathOptions={{ color: '#3FBFAD', weight: 2, opacity: 0.45, dashArray: '1 7', lineCap: 'round' }}
      />

      {propagationPath && (
        <Polyline
          positions={propagationPath}
          pathOptions={{ color: '#e2622d', weight: 3, opacity: 0.75 }}
        />
      )}

      {/* Historical flood event markers (optional layer) */}
      {(historicalEvents || []).map((ev) => (
        <CircleMarker
          key={ev.id}
          center={[ev.lat, ev.lon]}
          radius={5}
          pathOptions={{
            fillColor: '#c4262e',
            fillOpacity: 0.55,
            color: '#f2b8b8',
            weight: 1,
            dashArray: '2 2',
          }}
        >
          <Tooltip direction="top" offset={[0, -6]} opacity={0.95}>
            <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '11px' }}>
              <strong>{ev.location_name}</strong> &middot; {ev.event_date}
              <br />
              {ev.flood_type?.replace(/_/g, ' ')}
            </div>
          </Tooltip>
        </CircleMarker>
      ))}

      {/* Ad-hoc clicked-point query marker */}
      {queryPoint && (
        <CircleMarker
          center={[queryPoint.lat, queryPoint.lon]}
          radius={9}
          pathOptions={{
            fillColor: queryPoint.result ? riskColor(queryPoint.result.risk_level) : '#3FBFAD',
            fillOpacity: 0.85,
            color: '#ffffff',
            weight: 2,
          }}
        >
          <Popup>
            <div style={{ fontFamily: 'IBM Plex Mono, monospace', minWidth: '160px' }}>
              {queryPoint.loading && <div>Assessing this point...</div>}
              {queryPoint.error && <div>Could not assess this point.</div>}
              {queryPoint.result && (
                <>
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>
                    Near {queryPoint.result.location?.nearest_station || 'unmonitored ground'}
                  </div>
                  <div>
                    Risk:{' '}
                    <span style={{ color: riskColor(queryPoint.result.risk_level) }}>
                      {queryPoint.result.risk_level}
                    </span>{' '}
                    ({formatPct(queryPoint.result.risk_probability)})
                  </div>
                  <div>Rain 24h: {formatMm(queryPoint.result.rainfall?.rain_24h)}</div>
                  <div>Confidence: {queryPoint.result.confidence?.confidence_level}</div>
                </>
              )}
            </div>
          </Popup>
        </CircleMarker>
      )}

      {locData.map((loc) => {
        const level = loc.risk_level || 'LOW';
        const color = riskColor(level);
        const radius = RISK_RADIUS[level] || 7;
        const name = loc.location?.name || loc.location?.nearest_station || 'Unknown';
        const isSelected = selectedLocation === loc.location?.name || selectedLocation === name;
        const lat = loc.location?.lat;
        const lon = loc.location?.lon;
        if (!lat || !lon) return null;

        return (
          <CircleMarker
            key={name}
            center={[lat, lon]}
            radius={isSelected ? radius + 4 : radius}
            pathOptions={{
              fillColor: color,
              fillOpacity: isSelected ? 0.95 : 0.8,
              color: isSelected ? '#ffffff' : color,
              weight: isSelected ? 3 : 1.5,
            }}
            eventHandlers={{
              click: () => onLocationSelect && onLocationSelect(loc),
            }}
          >
            <Tooltip
              direction="top"
              offset={[0, -8]}
              opacity={0.95}
              permanent
              className="place-label"
            >
              <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px' }}>
                <strong>{name}</strong>
                <br />
                Risk: <span style={{ color }}>{level}</span>
                {loc.risk_probability != null && <> ({formatPct(loc.risk_probability)})</>}
              </div>
            </Tooltip>

            <Popup>
              <div style={{ fontFamily: 'IBM Plex Mono, monospace', minWidth: '170px' }}>
                <h4 style={{ margin: '0 0 6px 0', fontFamily: 'Space Grotesk, sans-serif' }}>{name}</h4>
                <div>
                  Risk: <span style={{ color }}>{level}</span> ({formatPct(loc.risk_probability, 1)})
                </div>
                {loc.rainfall && <div>Rain 24h: {formatMm(loc.rainfall.rain_24h)}</div>}
                {loc.cascade && <div>Cascade: {loc.cascade.cascade_risk_level}</div>}
                {loc.confidence && <div>Confidence: {loc.confidence.confidence_level}</div>}
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}

export default FloodMap;
