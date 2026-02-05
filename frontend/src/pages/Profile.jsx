import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { users } from '../api';
import './Profile.css';

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    title: '',
  });
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
      });
    }
  }, [user]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setMessage({ type: '', text: '' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      await users.updateMe(form);
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
        <button onClick={() => navigate(-1)} className="btn-back">← Back</button>
        <h1>Profile Settings</h1>
      </header>

      <main className="profile-main">
        <form onSubmit={handleSubmit} className="profile-form">
          {message.text && (
            <div className={`profile-message ${message.type}`}>
              {message.text}
            </div>
          )}
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
