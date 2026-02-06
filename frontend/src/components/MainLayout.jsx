import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useUserStatus } from '../context/UserStatusContext';
import { rooms, users as usersApi } from '../api';
import AIPromptPanel from './AIPromptPanel';
import Avatar from './Avatar';
import EmojiPicker from './EmojiPicker';
import { SearchIcon, PlusIcon, SparklesIcon, SunIcon, MoonIcon, SettingsIcon, LogOutIcon, HashIcon, GlobeIcon, getStatusIcon } from './icons';
import './Avatar.css';
import './MainLayout.css';

export default function MainLayout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { status: userStatus, setStatusType, setStatusEmoji, setAuto, manualOverride } = useUserStatus();
  const navigate = useNavigate();
  const location = useLocation();
  const [roomList, setRoomList] = useState([]);
  const [userList, setUserList] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newRoom, setNewRoom] = useState({ name: '', description: '' });
  const [createError, setCreateError] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [showStatusPicker, setShowStatusPicker] = useState(false);
  const [contactError, setContactError] = useState(null);
  const statusEmojiAnchorRef = useRef(null);

  useEffect(() => {
    Promise.all([rooms.list(), usersApi.list()])
      .then(([roomsRes, usersRes]) => {
        setRoomList(roomsRes.data);
        const apiUsers = (usersRes.data || []).map((u) => ({ ...u, status: u.status || 'deactive' }));
        setUserList(apiUsers);
      })
      .catch(() => {
        setRoomList([]);
        setUserList([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredRooms = roomList.filter(
    (r) =>
      !search ||
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description || '').toLowerCase().includes(search.toLowerCase())
  );
  const filteredUsers = userList.filter(
    (u) =>
      !search ||
      (u.username || '').toLowerCase().includes(search.toLowerCase()) ||
      (u.first_name || '').toLowerCase().includes(search.toLowerCase()) ||
      (u.last_name || '').toLowerCase().includes(search.toLowerCase())
  );

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    setCreateError(null);
    const payload = { name: newRoom.name.trim(), description: (newRoom.description || '').trim() };
    if (!payload.name) {
      setCreateError('Room name is required');
      return;
    }
    try {
      const { data } = await rooms.create(payload);
      setRoomList((prev) => [data, ...prev]);
      setNewRoom({ name: '', description: '' });
      setShowCreateModal(false);
      navigate(`/room/${data.id}`);
    } catch (err) {
      const d = err.response?.data;
      const msg = d?.name?.[0] ?? d?.description?.[0] ?? d?.detail ?? err.message ?? 'Failed to create room';
      setCreateError(typeof msg === 'string' ? msg : String(msg));
    }
  };

  const handleUserClick = async (targetUser) => {
    setContactError(null);
    try {
      const { data } = await rooms.dm(targetUser.id);
      setRoomList((prev) => {
        const exists = prev.some((r) => r.id === data.id);
        return exists ? prev : [data, ...prev];
      });
      navigate(`/room/${data.id}`);
    } catch (err) {
      const msg = err.response?.data?.error ?? err.response?.data?.detail ?? err.message ?? 'Failed to start conversation';
      setContactError(typeof msg === 'string' ? msg : 'Failed to start conversation');
    }
  };

  const isInRoom = (path) => path.startsWith('/room/');

  return (
    <div className="main-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="logo-text">
            <img src="/trutim-icon.svg" alt="Trutim" className="logo-icon" />
            Trutim
          </h1>
        </div>

        <button
          className="sidebar-create-btn"
          onClick={() => { setShowCreateModal(true); setCreateError(null); }}
          title="Create new room"
        >
          <PlusIcon size={18} />
          New Room
        </button>

        <div className="sidebar-search">
          <SearchIcon size={18} className="search-icon-svg" />
          <input
            type="text"
            placeholder="Search users or rooms..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setContactError(null); }}
            className="search-input"
          />
        </div>

        {contactError && (
          <div className="sidebar-contact-error" role="alert">
            {contactError}
            <button type="button" onClick={() => setContactError(null)} className="contact-error-dismiss" aria-label="Dismiss">×</button>
          </div>
        )}

        <div className="sidebar-list">
          {loading ? (
            <div className="sidebar-loading">Loading...</div>
          ) : (
            <>
              {filteredRooms.length > 0 && (
                <div className="sidebar-section">
                  <div className="section-label">Rooms</div>
                  <ul className="item-list">
                    {filteredRooms.map((room) => (
                      <li
                        key={room.id}
                        className={`sidebar-item ${isInRoom(location.pathname) && location.pathname === `/room/${room.id}` ? 'active' : ''}`}
                        onClick={() => navigate(`/room/${room.id}`)}
                      >
                        <HashIcon size={16} className="item-icon" />
                        <span className="item-name">{room.name}</span>
                        {room.member_count > 0 && (
                          <span className="item-meta">{room.member_count}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {filteredUsers.length > 0 && (
                <div className="sidebar-section">
                  <div className="section-label">Contacts</div>
                  <ul className="item-list">
                    {filteredUsers.map((u) => (
                      <li
                        key={u.id}
                        className="sidebar-item"
                        onClick={() => handleUserClick(u)}
                      >
                        <Avatar user={u} size={28} />
                        <span className="item-name">{u.username}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!loading && filteredRooms.length === 0 && filteredUsers.length === 0 && (
                <div className="sidebar-empty">
                  {search ? 'No results found' : 'No rooms or contacts yet'}
                </div>
              )}
            </>
          )}
        </div>
      </aside>

      <div className="main-content">
        <header className="main-header">
          <div className="header-left">
            <button
              className={`nav-tab ${location.pathname === '/' ? 'active' : ''}`}
              onClick={() => navigate('/')}
            >
              Dashboard
            </button>
            <button
              className={`nav-tab ${location.pathname === '/map' ? 'active' : ''}`}
              onClick={() => navigate('/map')}
            >
              <GlobeIcon size={16} /> Map
            </button>
          </div>
          <div className="header-right">
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <SunIcon size={20} /> : <MoonIcon size={20} />}
          </button>
          <button
            className="header-ai-btn"
            onClick={() => setShowAIPanel(true)}
            title="Open AI Assistant"
          >
            <SparklesIcon size={18} />
            AI
          </button>
          <div className="header-user">
            <button
              className="user-menu-btn"
              onClick={() => setShowUserMenu(!showUserMenu)}
              title="Account"
            >
              <Avatar user={{ ...user, status: userStatus.type }} size={32} />
              <span className="user-status-emoji" title="Your status">{userStatus.emoji}</span>
              <span className="user-name">{user?.username}</span>
              {user?.title && <span className="user-title">{user.title}</span>}
              <span className="menu-chevron">▼</span>
            </button>
            {showUserMenu && (
              <>
                <div className="menu-backdrop" onClick={() => { setShowUserMenu(false); setShowStatusPicker(false); }} />
                <div className="user-dropdown">
                  <div className="status-picker-section">
                    <span className="status-picker-label">Set your status</span>
                    <div className="status-type-btns">
                      <button
                        type="button"
                        className={`status-type-btn status-auto-btn ${!manualOverride ? 'active' : ''}`}
                        onClick={setAuto}
                        title="Auto (based on activity)"
                      >
                        Auto
                      </button>
                      {['active', 'idle', 'deactive'].map((t) => (
                        <button
                          key={t}
                          type="button"
                          className={`status-type-btn ${manualOverride && userStatus.type === t ? 'active' : ''}`}
                          onClick={() => setStatusType(t)}
                          title={t.charAt(0).toUpperCase() + t.slice(1)}
                        >
                          {getStatusIcon(t, { size: 12 })}
                        </button>
                      ))}
                    </div>
                    <div className="status-emoji-row">
                      <span>Emoji:</span>
                      <button
                        ref={statusEmojiAnchorRef}
                        type="button"
                        className="status-emoji-btn"
                        onClick={(e) => { e.stopPropagation(); setShowStatusPicker(!showStatusPicker); }}
                        title="Pick emoji"
                      >
                        {userStatus.emoji}
                      </button>
                      <EmojiPicker
                        onSelect={(emoji) => { setStatusEmoji(emoji); setShowStatusPicker(false); }}
                        visible={showStatusPicker}
                        onClose={() => setShowStatusPicker(false)}
                        theme={theme}
                        anchorRef={statusEmojiAnchorRef}
                      />
                    </div>
                  </div>
                  <button onClick={() => { navigate('/profile'); setShowUserMenu(false); }}>
                    <SettingsIcon size={16} /> Profile Settings
                  </button>
                  <button onClick={() => { logout(); setShowUserMenu(false); }} className="logout-btn">
                    <LogOutIcon size={16} /> Logout
                  </button>
                </div>
              </>
            )}
          </div>
          </div>
        </header>
        <div className="main-outlet">
          <Outlet />
        </div>
      </div>

      <AIPromptPanel isOpen={showAIPanel} onClose={() => setShowAIPanel(false)} />

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create Room</h2>
            <form onSubmit={handleCreateRoom}>
              {createError && <p className="create-error">{createError}</p>}
              <input
                placeholder="Room name"
                value={newRoom.name}
                onChange={(e) => setNewRoom({ ...newRoom, name: e.target.value })}
                required
                autoFocus
              />
              <input
                placeholder="Description (optional)"
                value={newRoom.description}
                onChange={(e) => setNewRoom({ ...newRoom, description: e.target.value })}
              />
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Create</button>
                <button type="button" onClick={() => setShowCreateModal(false)} className="btn-outline">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
