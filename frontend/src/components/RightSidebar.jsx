import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { users as usersApi, rooms } from '../api';
import Avatar from './Avatar';
import {
  MailIcon,
  MapPinIcon,
  LinkIcon,
  FileIcon,
  HashIcon,
  XIcon,
} from './icons';
import './RightSidebar.css';

function UserInfoPanel({ userId, onClose }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    usersApi
      .get(userId)
      .then(({ data }) => setUser(data))
      .catch(() => setError('Failed to load user'))
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <div className="right-sidebar-loading">Loading...</div>;
  if (error) return <div className="right-sidebar-error">{error}</div>;
  if (!user) return null;

  const contactLinks = [];
  if (user.github) contactLinks.push({ label: 'GitHub', url: user.github, icon: 'github' });
  if (user.twitter) contactLinks.push({ label: 'Twitter', url: user.twitter, icon: 'twitter' });
  if (user.facebook) contactLinks.push({ label: 'Facebook', url: user.facebook, icon: 'facebook' });
  if (user.instagram) contactLinks.push({ label: 'Instagram', url: user.instagram, icon: 'instagram' });
  if (user.youtube) contactLinks.push({ label: 'YouTube', url: user.youtube, icon: 'youtube' });

  const contactInfo = [];
  if (user.gmail) contactInfo.push({ label: 'Gmail', value: user.gmail });
  if (user.email && user.email !== user.gmail) contactInfo.push({ label: 'Email', value: user.email });
  if (user.telegram) contactInfo.push({ label: 'Telegram', value: user.telegram });
  if (user.discord) contactInfo.push({ label: 'Discord', value: user.discord });
  if (user.whatsapp) contactInfo.push({ label: 'WhatsApp', value: user.whatsapp });

  const resumeUrl = user.resume
    ? (user.resume.startsWith('http') || user.resume.startsWith('/') ? user.resume : `/${user.resume}`)
    : null;

  return (
    <div className="right-sidebar-panel">
      <div className="right-sidebar-top-bar">
        <button className="right-sidebar-close" onClick={onClose} title="Close">
          <XIcon size={18} />
        </button>
      </div>
      <div className="right-sidebar-header">
        <div className="right-sidebar-avatar-wrap">
          <Avatar user={user} size={72} />
        </div>
        <h2 className="right-sidebar-name">
          {user.first_name} {user.last_name}
        </h2>
        <span className="right-sidebar-username">@{user.username}</span>
        {user.title && <span className="right-sidebar-title">{user.title}</span>}
      </div>
      <div className="right-sidebar-body">
        {user.address && (
          <div className="right-sidebar-section">
            <div className="section-label">
              <MapPinIcon size={14} /> Location
            </div>
            <p>{user.address}</p>
          </div>
        )}
        {contactInfo.length > 0 && (
          <div className="right-sidebar-section">
            <div className="section-label">
              <MailIcon size={14} /> Contact
            </div>
            <ul className="info-list">
              {contactInfo.map(({ label, value }) => (
                <li key={label}>
                  <span className="info-label">{label}:</span> {value}
                </li>
              ))}
            </ul>
          </div>
        )}
        {contactLinks.length > 0 && (
          <div className="right-sidebar-section">
            <div className="section-label">
              <LinkIcon size={14} /> Public links
            </div>
            <ul className="info-list links-list">
              {contactLinks.map(({ label, url }) => (
                <li key={label}>
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        {resumeUrl && (
          <div className="right-sidebar-section">
            <div className="section-label">
              <FileIcon size={14} /> Resume
            </div>
            <a
              href={resumeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="resume-download-link"
            >
              View / Download resume
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

function CompanyMembersPanel({ companyId, onClose }) {
  const [room, setRoom] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!companyId) return;
    setLoading(true);
    setError(null);
    rooms
      .get(companyId)
      .then(({ data }) => setRoom(data))
      .catch(() => setError('Failed to load company'))
      .finally(() => setLoading(false));
  }, [companyId]);

  if (loading) return <div className="right-sidebar-loading">Loading...</div>;
  if (error) return <div className="right-sidebar-error">{error}</div>;
  if (!room) return null;

  const memberList = room.members || [];
  const owner = room.created_by;

  return (
    <div className="right-sidebar-panel">
      <div className="right-sidebar-top-bar">
        <button className="right-sidebar-close" onClick={onClose} title="Close">
          <XIcon size={18} />
        </button>
      </div>
      <div className="right-sidebar-header">
        <div className="right-sidebar-avatar-wrap">
          {room.avatar ? (
            <img
              src={room.avatar.startsWith('/') ? room.avatar : `/${room.avatar}`}
              alt={room.name}
              className="company-avatar-img"
            />
          ) : (
            <div className="company-icon-wrap">
              <HashIcon size={32} />
            </div>
          )}
        </div>
        <h2 className="right-sidebar-name">{room.name}</h2>
        {room.description && (
          <p className="right-sidebar-desc">{room.description}</p>
        )}
        {owner && (
          <div className="company-owner-wrap">
            <span className="company-owner-label">Owner</span>
            <button
              type="button"
              className="company-owner-btn"
              onClick={() => navigate(`/contact/${owner.id}`)}
            >
              <Avatar user={owner} size={24} showStatus={false} />
              <span>{owner.username}</span>
            </button>
          </div>
        )}
        <span className="right-sidebar-meta">
          {memberList.length} member{memberList.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="right-sidebar-body">
        <div className="right-sidebar-section">
          <div className="section-label">Members</div>
          <ul className="members-list">
            {memberList.map((m) => (
              <li
                key={m.id}
                className="member-item"
                onClick={() => navigate(`/contact/${m.id}`)}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/contact/${m.id}`)}
                role="button"
                tabIndex={0}
              >
                <Avatar user={m} size={36} />
                <div className="member-info">
                  <span className="member-name">{m.username}</span>
                  {m.title && <span className="member-title">{m.title}</span>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function RightSidebar({ type, id, onClose }) {
  if (!type || !id) return null;

  if (type === 'user') {
    return <UserInfoPanel userId={parseInt(id, 10)} onClose={onClose} />;
  }
  if (type === 'company') {
    return <CompanyMembersPanel companyId={parseInt(id, 10)} onClose={onClose} />;
  }
  return null;
}
