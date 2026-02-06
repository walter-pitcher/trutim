import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Outlet, NavLink } from 'react-router-dom';
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
      !r.is_direct &&
      (!search ||
        r.name.toLowerCase().includes(search.toLowerCase()) ||
        (r.description || '').toLowerCase().includes(search.toLowerCase()))
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
      setCreateError('Company name is required');
      return;
    }
    try {
      const { data } = await rooms.create(payload);
      setRoomList((prev) => [data, ...prev]);
      setNewRoom({ name: '', description: '' });
      setShowCreateModal(false);
      navigate(`/company/${data.id}`);
    } catch (err) {
      const d = err.response?.data;
      const msg = d?.name?.[0] ?? d?.description?.[0] ?? d?.detail ?? err.message ?? 'Failed to create company';
      setCreateError(typeof msg === 'string' ? msg : String(msg));
    }
  };

  const contactUserIdMatch = location.pathname.match(/^\/contact\/(\d+)$/);
  const currentContactUserId = contactUserIdMatch ? parseInt(contactUserIdMatch[1], 10) : null;
  const isContactActive = (user) => currentContactUserId === user.id;

  return (
    <div className="main-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="logo-text">
            <img src="/trutim.png" alt="Trutim" className="logo-icon" />
            Trutim
          </h1>
        </div>

        <button
          className="sidebar-create-btn"
          onClick={() => { setShowCreateModal(true); setCreateError(null); }}
          title="Create new company"
        >
          <PlusIcon size={18} />
          New Company
        </button>

        <div className="sidebar-search">
          <SearchIcon size={18} className="search-icon-svg" />
          <input
            type="text"
            placeholder="Search contacts or companies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="sidebar-list">
          {loading ? (
            <div className="sidebar-loading">Loading...</div>
          ) : (
            <>
              {filteredRooms.length > 0 && (
                <div className="sidebar-section">
                  <div className="section-label">Companies</div>
                  <ul className="item-list">
                    {filteredRooms.map((room) => (
                      <li key={room.id}>
                        <NavLink
                          to={`/company/${room.id}`}
                          className={({ isActive }) => `sidebar-item ${isActive ? 'active' : ''}`}
                        >
                          <HashIcon size={16} className="item-icon" />
                          <span className="item-name">{room.name}</span>
                          {room.member_count > 0 && (
                            <span className="item-meta">{room.member_count}</span>
                          )}
                        </NavLink>
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
                      <li key={u.id}>
                        <NavLink
                          to={`/contact/${u.id}`}
                          className={({ isActive }) => `sidebar-item ${isActive ? 'active' : ''}`}
                        >
                          <Avatar user={u} size={28} />
                          <span className="item-name">{u.username}</span>
                        </NavLink>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!loading && filteredRooms.length === 0 && filteredUsers.length === 0 && (
                <div className="sidebar-empty">
                  {search ? 'No results found' : 'No companies or contacts yet'}
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
            <h2>Create Company</h2>
            <form onSubmit={handleCreateRoom}>
              {createError && <p className="create-error">{createError}</p>}
              <input
                placeholder="Company name"
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
