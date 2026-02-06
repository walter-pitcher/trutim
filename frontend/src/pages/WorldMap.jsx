import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { users } from '../api';
import { GlobeIcon } from '../components/icons';
import './WorldMap.css';

export default function WorldMap() {
  const [regions, setRegions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    users
      .locationStats()
      .then(({ data }) => {
        setRegions(data.regions || []);
        setTotal(data.total || 0);
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'Failed to load map data');
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="world-map-page">
        <div className="world-map-loading">
          <div className="spinner" />
          <p>Loading user locations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="world-map-page">
        <div className="world-map-error">
          <GlobeIcon size={48} />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const maxCount = Math.max(1, ...regions.map((r) => r.count));
  const getRadius = (count) => Math.max(8, Math.min(40, 8 + (count / maxCount) * 32));
  const getOpacity = (count) => 0.3 + (count / maxCount) * 0.5;

  return (
    <div className="world-map-page">
      <header className="world-map-header">
        <h1>
          <GlobeIcon size={24} /> User Map
        </h1>
        <p className="world-map-subtitle">
          {total} user{total !== 1 ? 's' : ''} with location set
          {total === 0 && ' — Set your location in Profile Settings to appear here'}
        </p>
      </header>
      <div className="world-map-container">
        <MapContainer
          center={[20, 0]}
          zoom={2}
          className="world-map"
          minZoom={2}
          maxZoom={12}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {regions.map((r, i) => (
            <CircleMarker
              key={`${r.lat}-${r.lng}-${i}`}
              center={[r.lat, r.lng]}
              radius={getRadius(r.count)}
              pathOptions={{
                fillColor: 'var(--accent)',
                color: 'var(--accent-hover)',
                weight: 1.5,
                opacity: 0.9,
                fillOpacity: getOpacity(r.count),
              }}
              eventHandlers={{
                mouseover: (e) => {
                  e.target.setStyle({ weight: 3 });
                  e.target.bringToFront();
                },
                mouseout: (e) => {
                  e.target.setStyle({ weight: 1.5 });
                },
              }}
            >
              <Popup>
                <strong>{r.count} user{r.count !== 1 ? 's' : ''}</strong>
                <br />
                <span className="popup-coords">
                  {r.lat.toFixed(2)}°, {r.lng.toFixed(2)}°
                </span>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
