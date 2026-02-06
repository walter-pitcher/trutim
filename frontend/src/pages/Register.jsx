import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { SunIcon, MoonIcon } from '../components/icons';
import './Auth.css';

export default function Register() {
  const [form, setForm] = useState({
    username: '', email: '', password: '', first_name: '', last_name: '', title: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(form);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <button
        className="auth-theme-toggle"
        onClick={toggleTheme}
        title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <SunIcon size={22} /> : <MoonIcon size={22} />}
      </button>
      <div className="auth-card">
        <div className="auth-header">
          <h1 className="logo-text">
            <img src="/trutim-icon.svg" alt="Trutim" className="logo-icon" />
            Trutim
          </h1>
          <p>Real-time chat, video calls & collaboration for engineers</p>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}
          <input
            name="username"
            placeholder="Username"
            value={form.username}
            onChange={handleChange}
            required
          />
          <input
            name="email"
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
          />
          <input
            name="password"
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
            required
          />
          <input
            name="first_name"
            placeholder="First name"
            value={form.first_name}
            onChange={handleChange}
          />
          <input
            name="last_name"
            placeholder="Last name"
            value={form.last_name}
            onChange={handleChange}
          />
          <input
            name="title"
            placeholder="Title (e.g. Senior Engineer)"
            value={form.title}
            onChange={handleChange}
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
        <p className="auth-footer">
          Have an account? <Link to="/login">Sign In</Link>
        </p>
      </div>
    </div>
  );
}
