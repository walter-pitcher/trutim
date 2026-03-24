import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

const PROVIDERS = new Set(['google', 'github']);

export default function OAuthCallback() {
  const { provider } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { oauthLogin } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const runOAuth = async () => {
      const normalizedProvider = (provider || '').toLowerCase();
      if (!PROVIDERS.has(normalizedProvider)) {
        setError('Unsupported OAuth provider');
        return;
      }

      const callbackError = params.get('error');
      if (callbackError) {
        setError(`OAuth failed: ${callbackError}`);
        return;
      }

      const code = params.get('code');
      const state = params.get('state');
      const storedState = localStorage.getItem('oauth_state');
      const redirectUri = `${window.location.origin}/oauth/callback/${normalizedProvider}`;

      if (!code) {
        setError('Missing OAuth code');
        return;
      }
      if (!state || state !== storedState) {
        setError('OAuth state mismatch. Please try again.');
        return;
      }

      try {
        await oauthLogin(normalizedProvider, code, redirectUri);
        localStorage.removeItem('oauth_state');
        navigate('/', { replace: true });
      } catch (err) {
        setError(err.response?.data?.error || err.response?.data?.detail || 'OAuth login failed');
      }
    };

    runOAuth();
  }, [provider, params, navigate, oauthLogin]);

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <h1 className="logo-text">
            <img src="/trutim.png" alt="Trutim" className="logo-icon" />
            Trutim
          </h1>
          <p>Signing you in with OAuth...</p>
        </div>
        {error && (
          <>
            <div className="auth-error">{error}</div>
            <p className="auth-footer">
              <Link to="/login">Back to Sign In</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
