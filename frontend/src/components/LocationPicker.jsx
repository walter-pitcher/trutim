import { useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPinIcon } from './icons';
import './LocationPicker.css';

// Fix Leaflet default icon (broken with bundlers)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org';

async function geocodeAddress(query) {
  const res = await fetch(
    `${NOMINATIM_URL}/search?q=${encodeURIComponent(query)}&format=json&limit=1`,
    { headers: { 'Accept-Language': 'en' } }
  );
  const data = await res.json();
  if (data?.[0]) {
    const { lat, lon, display_name } = data[0];
    return { lat: parseFloat(lat), lng: parseFloat(lon), address: display_name };
  }
  return null;
}

async function reverseGeocode(lat, lng) {
  const res = await fetch(
    `${NOMINATIM_URL}/reverse?lat=${lat}&lon=${lng}&format=json`,
    { headers: { 'Accept-Language': 'en' } }
  );
  const data = await res.json();
  return data?.display_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function MapClickHandler({ onLocationSelect }) {
  useMapEvents({
    click(e) {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function LocationPicker({ value, onChange, disabled }) {
  const { lat, lng, address } = value || {};
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [geocodeError, setGeocodeError] = useState(null);
  const lastGeocodeRef = useRef(0);

  const handleLocationSelect = useCallback(async (newLat, newLng) => {
    setGeocodeError(null);
    try {
      const addr = await reverseGeocode(newLat, newLng);
      onChange({ lat: newLat, lng: newLng, address: addr });
    } catch (err) {
      onChange({ lat: newLat, lng: newLng, address: `${newLat.toFixed(4)}, ${newLng.toFixed(4)}` });
    }
  }, [onChange]);

  const handleSearch = async (e) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) return;
    setSearching(true);
    setGeocodeError(null);
    try {
      const now = Date.now();
      if (now - lastGeocodeRef.current < 1100) {
        await new Promise((r) => setTimeout(r, 1100 - (now - lastGeocodeRef.current)));
      }
      lastGeocodeRef.current = Date.now();
      const result = await geocodeAddress(q);
      if (result) {
        onChange(result);
        setSearchQuery('');
      } else {
        setGeocodeError('Address not found');
      }
    } catch (err) {
      setGeocodeError('Search failed. Try again.');
    } finally {
      setSearching(false);
    }
  };

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      setGeocodeError('Geolocation not supported');
      return;
    }
    setGeocodeError(null);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        await handleLocationSelect(latitude, longitude);
      },
      () => setGeocodeError('Could not get your location')
    );
  };

  const center = lat != null && lng != null ? [lat, lng] : [20, 0];
  const zoom = lat != null && lng != null ? 12 : 2;

  return (
    <div className="location-picker">
      <div className="location-picker-controls">
        <form onSubmit={handleSearch} className="location-search-form">
          <input
            type="text"
            placeholder="Search address (e.g. 123 Main St, New York)"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setGeocodeError(null); }}
            disabled={disabled}
          />
          <button type="submit" disabled={searching || disabled} className="btn-primary">
            {searching ? 'Searching...' : 'Search'}
          </button>
        </form>
        <button
          type="button"
          onClick={handleUseMyLocation}
          disabled={disabled}
          className="btn-use-location"
        >
          <MapPinIcon size={16} /> Use my location
        </button>
      </div>
      {geocodeError && <p className="location-error">{geocodeError}</p>}
      {address && (
        <div className="location-display-row">
          <p className="location-display">
            <MapPinIcon size={14} /> {address}
          </p>
          <button
            type="button"
            onClick={() => onChange(null)}
            disabled={disabled}
            className="btn-clear-location"
          >
            Clear
          </button>
        </div>
      )}
      <div className="location-map-wrapper">
        <MapContainer
          center={center}
          zoom={zoom}
          className="location-map"
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler onLocationSelect={handleLocationSelect} />
          {lat != null && lng != null && (
            <Marker position={[lat, lng]} />
          )}
        </MapContainer>
      </div>
      <p className="location-hint">Click on the map to set your exact location</p>
    </div>
  );
}
