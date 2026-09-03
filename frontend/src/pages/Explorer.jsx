/**
 * NeerNetra -- Explorer page
 * ============================
 * Analyst sandbox: cascade what-if simulator + point-to-point route
 * inspector. Independent of the live pilot scenario on the Dashboard.
 */

import { useState, useEffect } from 'react';
import CascadeExplorer from '../components/CascadeExplorer';
import RouteInspector from '../components/RouteInspector';
import { systemAPI } from '../services/api';

function Explorer() {
  const [locations, setLocations] = useState([]);

  useEffect(() => {
    systemAPI.getLocations()
      .then((res) => setLocations(res.data.locations || []))
      .catch(() => setLocations([]));
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Scenario explorer</h1>
        <p>Test what-if rainfall and routing scenarios beyond the live pilot readings.</p>
      </div>
      <div className="explorer-grid">
        <CascadeExplorer locations={locations} />
        <RouteInspector locations={locations} />
      </div>
    </div>
  );
}

export default Explorer;
