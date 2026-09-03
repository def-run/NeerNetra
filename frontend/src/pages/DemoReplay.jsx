/**
 * NeerNetra -- Demo Replay page
 * ===============================
 */

import DemoConsole from '../components/DemoConsole';

function DemoReplay() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Demo replay</h1>
        <p>Step through the June 2013 Kedarnath disaster as the system would have seen it unfold.</p>
      </div>
      <DemoConsole />
    </div>
  );
}

export default DemoReplay;
