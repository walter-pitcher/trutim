import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { SunIcon, MoonIcon } from '../components/icons';
import './Auth.css';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const beginOAuth = (provider) => {
    const providerName = provider.toLowerCase();
    const state = crypto.randomUUID();
    const redirectUri = `${window.location.origin}/oauth/callback/${providerName}`;
    localStorage.setItem('oauth_state', state);

    const envVarName =
      providerName === 'google' ? 'VITE_GOOGLE_CLIENT_ID' : 'VITE_GITHUB_CLIENT_ID';
    const clientId = import.meta.env[envVarName];
    if (!clientId) {
      setError(`${provider} OAuth is not configured on frontend`);
      return;
    }

    const params = new URLSearchParams({
      client_id: clientId,
      redirect_uri: redirectUri,
      state,
    });

    if (providerName === 'google') {
      params.set('response_type', 'code');
      params.set('scope', 'openid email profile');
      window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
      return;
    }

    params.set('scope', 'read:user user:email');
    window.location.href = `https://github.com/login/oauth/authorize?${params.toString()}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
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
            <img src="/trutim.png" alt="Trutim" className="logo-icon" />
            Trutim
          </h1>
          <p>Real-time chat, video calls & collaboration for engineers</p>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <div className="auth-divider">or continue with</div>
        <div className="oauth-buttons">
          <button
            type="button"
            className="oauth-button"
            onClick={() => beginOAuth('google')}
          >
            Continue with Google
          </button>
          <button
            type="button"
            className="oauth-button"
            onClick={() => beginOAuth('github')}
          >
            Continue with GitHub
          </button>
        </div>
        <p className="auth-footer">
          No account? <Link to="/register">Register</Link>
        </p>
      </div>
    </div>
  );
}
