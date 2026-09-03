/**
 * NeerNetra -- RainfallCard
 * ===========================
 * Rolling rainfall accumulation windows and current weather for the
 * selected location. Data arrives embedded in the risk-map response.
 */

function RainfallCard({ riskData }) {
  if (!riskData) {
    return (
      <div className="panel-card">
        <h3>Current rainfall</h3>
        <p className="stub-text">No data yet.</p>
      </div>
    );
  }

  const rain = riskData.rainfall || {};
  const weather = riskData.current_weather || {};
  const forecast = riskData.forecast || {};

  const windows = [
    { label: '1h', value: rain.rain_1h, threshold: 15 },
    { label: '3h', value: rain.rain_3h, threshold: 30 },
    { label: '6h', value: rain.rain_6h, threshold: 50 },
    { label: '12h', value: rain.rain_12h, threshold: 80 },
    { label: '24h', value: rain.rain_24h, threshold: 120 },
    { label: '72h', value: rain.rain_72h, threshold: 200 },
  ];

  return (
    <div className="panel-card">
      <h3>Current rainfall</h3>

      <div className="weather-row">
        {weather.temperature_c != null && <span className="weather-item">{weather.temperature_c}&deg;C</span>}
        {weather.humidity_pct != null && <span className="weather-item">{weather.humidity_pct}% humidity</span>}
        {weather.precipitation_mm != null && <span className="weather-item">{weather.precipitation_mm} mm/h now</span>}
        {rain.rainfall_intensity != null && <span className="weather-item">{rain.rainfall_intensity}x intensity</span>}
      </div>

      <div className="rain-windows">
        {windows.map((w) => {
          const val = w.value || 0;
          const pct = Math.min((val / w.threshold) * 100, 100);
          const isHigh = val > w.threshold * 0.7;
          return (
            <div key={w.label} className="rain-window-item">
              <div className="rain-bar-bg">
                <div className={`rain-bar-fill${isHigh ? ' rain-high' : ''}`} style={{ height: `${pct}%` }} />
              </div>
              <span className="rain-value">{val}</span>
              <span className="rain-label">{w.label}</span>
            </div>
          );
        })}
      </div>

      {(forecast.forecast_rain_3h != null || forecast.forecast_rain_6h != null) && (
        <div className="forecast-row">
          <span>Next few hours: </span>
          <span className="forecast-val">+3h {forecast.forecast_rain_3h || 0}mm</span>
          <span className="forecast-val">+6h {forecast.forecast_rain_6h || 0}mm</span>
        </div>
      )}
    </div>
  );
}

export default RainfallCard;
