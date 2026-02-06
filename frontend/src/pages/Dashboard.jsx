import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { MessageCircleIcon, UsersIcon, GlobeIcon } from '../components/icons';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="dashboard-welcome">
      <div className="dashboard-bg">
        <div className="dashboard-glow dashboard-glow-1" />
        <div className="dashboard-glow dashboard-glow-2" />
        <div className="dashboard-glow dashboard-glow-3" />
      </div>
      <div className="dashboard-hero">
        <div className="logo-3d-container">
          <div className="logo-3d-inner">
            <img src="/trutim.png" alt="Trutim" className="logo-3d-img" />
          </div>
        </div>
        <div className="welcome-content">
          <h1 className="dashboard-title">Welcome, {user?.username || 'User'}</h1>
          <p className="welcome-subtitle">
            Select a conversation from the sidebar or create a new company to get started.
          </p>
        </div>
      </div>
      <div className="dashboard-cards">
        <div className="dashboard-card">
          <MessageCircleIcon size={24} className="dashboard-card-icon" />
          <span>Create companies for team collaboration</span>
        </div>
        <div className="dashboard-card">
          <UsersIcon size={24} className="dashboard-card-icon" />
          <span>Click contacts to start direct messages</span>
        </div>
        <div
          className="dashboard-card dashboard-card-action"
          onClick={() => navigate('/map')}
          onKeyDown={(e) => e.key === 'Enter' && navigate('/map')}
          role="button"
          tabIndex={0}
        >
          <GlobeIcon size={24} className="dashboard-card-icon" />
          <span>View users on the world map</span>
        </div>
      </div>
    </div>
  );
}
