/**
 * NeerNetra -- Locations page
 * =============================
 * Directory of every monitored pilot location, with an inline quick
 * rainfall check per card.
 */

import { useState, useEffect } from 'react';
import LocationCard from '../components/LocationCard';
import { systemAPI } from '../services/api';

function Locations() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    systemAPI.getLocations()
      .then((res) => setData(res.data))
      .catch(() => setError(true));
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Monitored locations</h1>
        <p>
          {data ? `${data.total} locations across the Mandakini Valley pilot corridor.` : 'Loading the pilot network...'}
        </p>
      </div>

      {error && <p className="stub-text">Could not load the location directory.</p>}

      <div className="locations-grid">
        {(data?.locations || []).map((loc) => (
          <LocationCard key={loc.name} location={loc} />
        ))}
      </div>
    </div>
  );
}

export default Locations;
