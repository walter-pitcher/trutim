import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { MessageCircleIcon, UsersIcon, GlobeIcon } from '../components/icons';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="dashboard-welcome">
      <div className="welcome-illustration">
        <svg viewBox="0 0 200 160" className="welcome-svg" aria-hidden>
          <defs>
            <linearGradient id="welcome-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--accent)" />
              <stop offset="100%" stopColor="var(--accent-hover)" />
            </linearGradient>
            <filter id="welcome-glow">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <circle cx="100" cy="80" r="50" fill="url(#welcome-grad)" opacity="0.15" />
          <path d="M70 90c0-16.5 13.5-30 30-30s30 13.5 30 30v20H70V90z" fill="url(#welcome-grad)" opacity="0.3" />
          <path d="M85 95a15 15 0 1 1 30 0v25H85V95z" fill="url(#welcome-grad)" />
          <path d="M115 95a15 15 0 1 1 30 0v25H115V95z" fill="url(#welcome-grad)" opacity="0.7" />
          <path d="M100 65a15 15 0 1 1 0 30 15 15 0 0 1 0-30z" fill="url(#welcome-grad)" />
        </svg>
      </div>
      <div className="welcome-content">
        <h1>Welcome, {user?.username || 'User'}</h1>
        <p className="welcome-subtitle">
          Select a conversation from the sidebar or create a new room to get started.
        </p>
        <div className="welcome-hint">
          <span><MessageCircleIcon size={18} /> Create rooms for team collaboration</span>
          <span><UsersIcon size={18} /> Click contacts to start direct messages</span>
          <span
            className="welcome-hint-link"
            onClick={() => navigate('/map')}
            onKeyDown={(e) => e.key === 'Enter' && navigate('/map')}
            role="button"
            tabIndex={0}
          >
            <GlobeIcon size={18} /> View users on the world map
          </span>
        </div>
      </div>
    </div>
  );
}
