import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { users } from '../api';
import AvatarUpload from '../components/AvatarUpload';
import LocationPicker from '../components/LocationPicker';
import ResumeUpload from '../components/ResumeUpload';
import { ArrowLeftIcon } from '../components/icons';
import './Profile.css';

const SOCIAL_FIELDS = ['github', 'facebook', 'twitter', 'instagram', 'youtube'];

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    title: '',
    github: '',
    facebook: '',
    twitter: '',
    instagram: '',
    youtube: '',
    gmail: '',
    telegram: '',
    discord: '',
    whatsapp: '',
  });
  const [location, setLocation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    if (user) {
      setForm({
        username: user.username || '',
        email: user.email || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        title: user.title || '',
        github: user.github || '',
        facebook: user.facebook || '',
        twitter: user.twitter || '',
        instagram: user.instagram || '',
        youtube: user.youtube || '',
        gmail: user.gmail || '',
        telegram: user.telegram || '',
        discord: user.discord || '',
        whatsapp: user.whatsapp || '',
      });
      if (user.latitude != null && user.longitude != null) {
        setLocation({
          lat: parseFloat(user.latitude),
          lng: parseFloat(user.longitude),
          address: user.address || '',
        });
      } else {
        setLocation(null);
      }
    }
  }, [user]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setMessage({ type: '', text: '' });
  };

  const handleAvatarUpload = async (file) => {
    await users.uploadAvatar(file);
    await refreshUser();
    setMessage({ type: 'success', text: 'Avatar updated successfully.' });
  };

  const handleResumeUpload = async (file) => {
    await users.uploadResume(file);
    await refreshUser();
    setMessage({ type: 'success', text: 'Resume updated successfully.' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const payload = { ...form };
      if (location) {
        payload.latitude = location.lat;
        payload.longitude = location.lng;
        payload.address = location.address || '';
      } else {
        payload.latitude = null;
        payload.longitude = null;
        payload.address = '';
      }
      await users.updateMe(payload);
      await refreshUser();
      setMessage({ type: 'success', text: 'Profile updated successfully.' });
    } catch (err) {
      const d = err.response?.data;
      const msg = d?.username?.[0] ?? d?.email?.[0] ?? d?.detail ?? err.message ?? 'Failed to update profile';
      setMessage({ type: 'error', text: typeof msg === 'string' ? msg : String(msg) });
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="profile-page">
      <header className="profile-header">
        <button onClick={() => navigate(-1)} className="btn-back">
          <ArrowLeftIcon size={18} /> Back
        </button>
        <h1>Profile Settings</h1>
      </header>

      <main className="profile-main">
        <form onSubmit={handleSubmit} className="profile-form">
          {message.text && (
            <div className={`profile-message ${message.type}`}>
              {message.text}
            </div>
          )}
          <div className="profile-avatar-section">
            <AvatarUpload
              user={user}
              onUpload={handleAvatarUpload}
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              name="username"
              value={form.username}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="first_name">First name</label>
              <input
                id="first_name"
                name="first_name"
                value={form.first_name}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="last_name">Last name</label>
              <input
                id="last_name"
                name="last_name"
                value={form.last_name}
                onChange={handleChange}
              />
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="title">Title / Role</label>
            <input
              id="title"
              name="title"
              placeholder="e.g. Senior Engineer"
              value={form.title}
              onChange={handleChange}
            />
          </div>
          <div className="form-group">
            <label>Location</label>
            <LocationPicker
              value={location}
              onChange={setLocation}
              disabled={loading}
            />
          </div>

          <section className="profile-section">
            <h2 className="profile-section-title">Social Links</h2>
            {SOCIAL_FIELDS.map((field) => (
              <div key={field} className="form-group">
                <label htmlFor={field}>{field.charAt(0).toUpperCase() + field.slice(1)}</label>
                <input
                  id={field}
                  name={field}
                  type="url"
                  placeholder={`https://${field}.com/username`}
                  value={form[field]}
                  onChange={handleChange}
                />
              </div>
            ))}
          </section>

          <section className="profile-section">
            <h2 className="profile-section-title">Contact Info</h2>
            <div className="form-group">
              <label htmlFor="gmail">Gmail</label>
              <input
                id="gmail"
                name="gmail"
                type="email"
                placeholder="you@gmail.com"
                value={form.gmail}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="telegram">Telegram</label>
              <input
                id="telegram"
                name="telegram"
                placeholder="@username"
                value={form.telegram}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="discord">Discord</label>
              <input
                id="discord"
                name="discord"
                placeholder="username#1234"
                value={form.discord}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="whatsapp">WhatsApp</label>
              <input
                id="whatsapp"
                name="whatsapp"
                placeholder="+1234567890"
                value={form.whatsapp}
                onChange={handleChange}
              />
            </div>
          </section>

          <section className="profile-section">
            <h2 className="profile-section-title">Resume</h2>
            <ResumeUpload
              user={user}
              onUpload={handleResumeUpload}
              disabled={loading}
            />
          </section>

          <div className="form-actions">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save changes'}
            </button>
            <button type="button" onClick={() => navigate(-1)} className="btn-outline">
              Cancel
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
