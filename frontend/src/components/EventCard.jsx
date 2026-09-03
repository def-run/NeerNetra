/**
 * NeerNetra -- EventCard
 * ========================
 * One historical flood event, used in the History timeline.
 */

import { riskColor, formatDate } from '../utils/constants';

function EventCard({ event }) {
  const color = riskColor(event.severity);
  return (
    <div className="event-card" style={{ borderLeftColor: color }}>
      <div className="event-card-head">
        <span className="event-date">{formatDate(event.event_date)}</span>
        <span className="event-severity" style={{ color, borderColor: color }}>{event.severity}</span>
      </div>
      <h4 className="event-location">{event.location_name}</h4>
      <span className="event-type">{event.flood_type?.replace(/_/g, ' ')}</span>

      <p className="event-description">{event.description}</p>

      <div className="event-stats">
        <div className="event-stat">
          <span className="event-stat-val">{event.estimated_rainfall_24h_mm}mm</span>
          <span className="event-stat-label">24h rain</span>
        </div>
        <div className="event-stat">
          <span className="event-stat-val">{event.estimated_rainfall_72h_mm}mm</span>
          <span className="event-stat-label">72h rain</span>
        </div>
        <div className="event-stat">
          <span className="event-stat-val">{event.deaths}</span>
          <span className="event-stat-label">fatalities</span>
        </div>
      </div>

      {event.affected_locations?.length > 0 && (
        <div className="event-affected">
          {event.affected_locations.map((loc) => (
            <span key={loc} className="event-chip">{loc}</span>
          ))}
        </div>
      )}

      <span className="event-source">Source: {event.source}</span>
    </div>
  );
}

export default EventCard;
