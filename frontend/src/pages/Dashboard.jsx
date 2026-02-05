import { useAuth } from '../context/AuthContext';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="dashboard-welcome">
      <div className="welcome-content">
        <div className="welcome-icon">💬</div>
        <h1>Welcome, {user?.username || 'User'}</h1>
        <p className="welcome-subtitle">
          Select a conversation from the sidebar or create a new room to get started.
        </p>
        <div className="welcome-hint">
          <span>Create rooms for team collaboration</span>
          <span>Click contacts to start direct messages</span>
        </div>
      </div>
    </div>
  );
}
