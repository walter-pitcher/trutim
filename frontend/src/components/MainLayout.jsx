import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useUserStatus } from '../context/UserStatusContext';
import { usePresence } from '../context/PresenceContext';
import { rooms, users as usersApi } from '../api';
import AIPromptPanel from './AIPromptPanel';
import Avatar from './Avatar';
import RightSidebar from './RightSidebar';
import EmojiPicker from './EmojiPicker';
import { SearchIcon, PlusIcon, SparklesIcon, SunIcon, MoonIcon, SettingsIcon, LogOutIcon, HashIcon, GlobeIcon, ChevronLeftIcon, MenuIcon, XIcon, MessageCircleIcon, getStatusIcon } from './icons';
import './Avatar.css';
import './MainLayout.css';

export default function MainLayout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { status: userStatus, setStatusType, setStatusEmoji, setAuto, manualOverride } = useUserStatus();
  const { getStatus: getPresenceStatus } = usePresence();
  const navigate = useNavigate();
  const location = useLocation();
  const [roomList, setRoomList] = useState([]);
  const [userList, setUserList] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newRoom, setNewRoom] = useState({ name: '', description: '', avatar: null });
  const [createError, setCreateError] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [showStatusPicker, setShowStatusPicker] = useState(false);
  const [rightSidebarVisible, setRightSidebarVisible] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
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

  useEffect(() => {
    const handler = (e) => {
      const { roomId, type, contactUserId } = e.detail || {};
      if (type === 'company' && roomId) {
        setRoomList((prev) => {
          const idx = prev.findIndex((r) => r.id === roomId);
          if (idx <= 0) return prev;
          const [r] = prev.splice(idx, 1);
          return [r, ...prev];
        });
      } else if (type === 'contact' && contactUserId) {
        const uid = parseInt(contactUserId, 10);
        setUserList((prev) => {
          const idx = prev.findIndex((u) => u.id === uid);
          if (idx <= 0) return prev;
          const [u] = prev.splice(idx, 1);
          return [u, ...prev];
        });
      }
    };
    window.addEventListener('room-activity', handler);
    return () => window.removeEventListener('room-activity', handler);
  }, []);

  const filteredRooms = roomList.filter(
    (r) =>
      !r.is_direct &&
      (!search ||
        r.name.toLowerCase().includes(search.toLowerCase()) ||
        (r.description || '').toLowerCase().includes(search.toLowerCase()))
  );
  const filteredUsers = userList
    .filter(
      (u) =>
        !search ||
        (u.username || '').toLowerCase().includes(search.toLowerCase()) ||
        (u.first_name || '').toLowerCase().includes(search.toLowerCase()) ||
        (u.last_name || '').toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      const dmRooms = roomList.filter((r) => r.is_direct && r.dm_user);
      const lastAt = (userId) => {
        const dm = dmRooms.find((r) => r.dm_user?.id === userId);
        const ts = dm?.last_message?.created_at;
        return ts ? new Date(ts).getTime() : 0;
      };
      const ta = lastAt(a.id);
      const tb = lastAt(b.id);
      if (ta !== tb) return tb - ta;
      return (a.username || '').localeCompare(b.username || '');
    });

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    setCreateError(null);
    const name = newRoom.name.trim();
    const description = (newRoom.description || '').trim();
    if (!name) {
      setCreateError('Company name is required');
      return;
    }
    try {
      let data;
      if (newRoom.avatar) {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description);
        formData.append('avatar', newRoom.avatar);
        const res = await rooms.create(formData);
        data = res.data;
      } else {
        const res = await rooms.create({ name, description });
        data = res.data;
      }
      setRoomList((prev) => [data, ...prev]);
      setNewRoom({ name: '', description: '', avatar: null });
      setShowCreateModal(false);
      navigate(`/company/${data.id}`);
    } catch (err) {
      const d = err.response?.data;
      const msg = d?.name?.[0] ?? d?.description?.[0] ?? d?.avatar?.[0] ?? d?.detail ?? err.message ?? 'Failed to create company';
      setCreateError(typeof msg === 'string' ? msg : String(msg));
    }
  };

  const contactUserIdMatch = location.pathname.match(/^\/contact\/(\d+)$/);
  const companyIdMatch = location.pathname.match(/^\/company\/(\d+)$/);
  const currentContactUserId = contactUserIdMatch ? parseInt(contactUserIdMatch[1], 10) : null;
  const isContactActive = (user) => currentContactUserId === user.id;

  const rightSidebarType = contactUserIdMatch ? 'user' : companyIdMatch ? 'company' : null;
  const rightSidebarId = contactUserIdMatch?.[1] ?? companyIdMatch?.[1] ?? null;

  useEffect(() => {
    if (rightSidebarType && rightSidebarId) setRightSidebarVisible(true);
  }, [rightSidebarType, rightSidebarId]);

  return (
    <div className="main-layout">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <button className="sidebar-close-mobile" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar">
            <XIcon size={20} />
          </button>
          <h1 className="logo-text">
            <img src="/trutim.png" alt="Trutim" className="logo-icon" />
            Trutim
          </h1>
        </div>

        <button
          className="sidebar-create-btn"
          onClick={() => { setShowCreateModal(true); setCreateError(null); setNewRoom({ name: '', description: '', avatar: null }); }}
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
                          onClick={() => setSidebarOpen(false)}
                        >
                          {room.avatar ? (
                            <img
                              src={room.avatar.startsWith('/') ? room.avatar : `/${room.avatar}`}
                              alt=""
                              className="item-icon sidebar-room-avatar"
                            />
                          ) : (
                            <HashIcon size={16} className="item-icon" />
                          )}
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
                    {filteredUsers.map((u) => {
                      const liveStatus = getPresenceStatus(u.id) ?? u.status ?? 'deactive';
                      return (
                        <li key={u.id}>
                          <NavLink
                            to={`/contact/${u.id}`}
                            className={({ isActive }) => `sidebar-item ${isActive ? 'active' : ''}`}
                            onClick={() => setSidebarOpen(false)}
                          >
                            <Avatar user={{ ...u, status: liveStatus }} size={28} />
                            <span className="item-name">{u.username}</span>
                          </NavLink>
                        </li>
                      );
                    })}
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
      <div className="sidebar-backdrop" aria-hidden={!sidebarOpen} onClick={() => setSidebarOpen(false)} />

      <div className="main-content">
        <header className="main-header">
          <div className="header-left">
            <button className="sidebar-toggle-mobile" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar">
              <MenuIcon size={22} />
            </button>
            <button
              className={`nav-tab ${location.pathname === '/' ? 'active' : ''}`}
              onClick={() => navigate('/')}
            >
              <MessageCircleIcon size={16} className="nav-tab-icon" />
              <span className="nav-tab-label">Dashboard</span>
            </button>
            <button
              className={`nav-tab ${location.pathname === '/map' ? 'active' : ''}`}
              onClick={() => navigate('/map')}
            >
              <GlobeIcon size={16} className="nav-tab-icon" />
              <span className="nav-tab-label">Map</span>
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
            <span className="header-ai-label">AI</span>
          </button>
          <div className="header-user">
            <button
              className="user-menu-btn"
              onClick={() => setShowUserMenu(!showUserMenu)}
              title="Account"
            >
              <Avatar user={{ ...user, status: userStatus.type }} size={32} />
              <span className="user-status-emoji" title="Your status">{userStatus.emoji}</span>
              <span className="user-name header-user-name">{user?.username}</span>
              {user?.title && <span className="user-title header-user-title">{user.title}</span>}
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
                      {[
                        { value: 'active', label: 'Active' },
                        { value: 'idle', label: 'Idle' },
                        { value: 'deactive', label: 'Offline' },
                      ].map(({ value, label }) => (
                        <button
                          key={value}
                          type="button"
                          className={`status-type-btn ${manualOverride && userStatus.type === value ? 'active' : ''}`}
                          onClick={() => setStatusType(value)}
                          title={label}
                        >
                          {getStatusIcon(value, { size: 12 })}
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
        <div className="main-area">
          <div className="main-outlet">
            <Outlet />
          </div>
          {rightSidebarType && rightSidebarId && (
            <>
              {rightSidebarVisible ? (
                <aside className="right-sidebar">
                  <RightSidebar
                    type={rightSidebarType}
                    id={rightSidebarId}
                    onClose={() => setRightSidebarVisible(false)}
                    currentUserId={user?.id}
                    onCompanyUpdate={(updated) => {
                      setRoomList((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
                      window.dispatchEvent(new CustomEvent('company-updated', { detail: updated }));
                    }}
                  />
                </aside>
              ) : (
                <button
                  className="right-sidebar-toggle"
                  onClick={() => setRightSidebarVisible(true)}
                  title="Show sidebar"
                >
                  <ChevronLeftIcon size={18} />
                </button>
              )}
            </>
          )}
        </div>
      </div>

      <AIPromptPanel isOpen={showAIPanel} onClose={() => setShowAIPanel(false)} />

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create Company</h2>
            <form onSubmit={handleCreateRoom}>
              {createError && <p className="create-error">{createError}</p>}
              <div className="create-company-avatar-wrap">
                <label className="create-company-avatar-label">Company avatar (optional)</label>
                <div className="create-company-avatar-row">
                  <div className="create-company-avatar-preview">
                    {newRoom.avatar ? (
                      <img src={URL.createObjectURL(newRoom.avatar)} alt="Preview" />
                    ) : (
                      <span className="create-company-avatar-placeholder">?</span>
                    )}
                  </div>
                  <div className="create-company-avatar-btns">
                    <label className="btn-outline btn-sm">
                      Choose image
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/gif,image/webp"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) setNewRoom((r) => ({ ...r, avatar: f }));
                        }}
                        hidden
                      />
                    </label>
                    {newRoom.avatar && (
                      <button
                        type="button"
                        className="btn-outline btn-sm"
                        onClick={() => setNewRoom((r) => ({ ...r, avatar: null }))}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              </div>
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
