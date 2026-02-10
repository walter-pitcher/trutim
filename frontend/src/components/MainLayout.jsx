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
import { SearchIcon, PlusIcon, SparklesIcon, SunIcon, MoonIcon, SettingsIcon, LogOutIcon, HashIcon, GlobeIcon, ChevronLeftIcon, MenuIcon, XIcon, MessageCircleIcon, getStatusIcon, BanIcon, ArchiveIcon, BellOffIcon } from './icons';

const SIDEBAR_WIDTH_KEY = 'trutim-sidebar-width';
const SIDEBAR_MIN = 200;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 300;
const RIGHT_SIDEBAR_WIDTH_KEY = 'trutim-right-sidebar-width';
const RIGHT_SIDEBAR_MIN = 240;
const RIGHT_SIDEBAR_MAX = 500;
const RIGHT_SIDEBAR_DEFAULT = 320;
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
  const [showActionMenu, setShowActionMenu] = useState(false);
  const [companyContextMenu, setCompanyContextMenu] = useState(null);
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [channelForm, setChannelForm] = useState({ name: '', description: '' });
  const [channelError, setChannelError] = useState(null);
  const [pendingChannelRoom, setPendingChannelRoom] = useState(null);
  const [showCreateGroupModal, setShowCreateGroupModal] = useState(false);
  const [newGroup, setNewGroup] = useState({ name: '', description: '' });
  const [groupError, setGroupError] = useState(null);
  const [groupSearch, setGroupSearch] = useState('');
  const [selectedGroupUserIds, setSelectedGroupUserIds] = useState(new Set());
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem(SIDEBAR_WIDTH_KEY);
    const n = saved ? parseInt(saved, 10) : SIDEBAR_DEFAULT;
    return Number.isFinite(n) ? Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, n)) : SIDEBAR_DEFAULT;
  });
  const [rightSidebarWidth, setRightSidebarWidth] = useState(() => {
    const saved = localStorage.getItem(RIGHT_SIDEBAR_WIDTH_KEY);
    const n = saved ? parseInt(saved, 10) : RIGHT_SIDEBAR_DEFAULT;
    return Number.isFinite(n) ? Math.max(RIGHT_SIDEBAR_MIN, Math.min(RIGHT_SIDEBAR_MAX, n)) : RIGHT_SIDEBAR_DEFAULT;
  });
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(0);
  const rightResizeStartX = useRef(0);
  const rightResizeStartWidth = useRef(0);
  const statusEmojiAnchorRef = useRef(null);

  const handleResizeStart = (e) => {
    e.preventDefault();
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = sidebarWidth;
    const onMove = (ev) => {
      const dx = ev.clientX - resizeStartX.current;
      const next = Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, resizeStartWidth.current + dx));
      setSidebarWidth(next);
      resizeStartX.current = ev.clientX;
      resizeStartWidth.current = next;
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      localStorage.setItem(SIDEBAR_WIDTH_KEY, String(resizeStartWidth.current));
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  const handleRightResizeStart = (e) => {
    e.preventDefault();
    rightResizeStartX.current = e.clientX;
    rightResizeStartWidth.current = rightSidebarWidth;
    const onMove = (ev) => {
      const dx = ev.clientX - rightResizeStartX.current;
      const next = Math.max(RIGHT_SIDEBAR_MIN, Math.min(RIGHT_SIDEBAR_MAX, rightResizeStartWidth.current - dx));
      setRightSidebarWidth(next);
      rightResizeStartX.current = ev.clientX;
      rightResizeStartWidth.current = next;
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      localStorage.setItem(RIGHT_SIDEBAR_WIDTH_KEY, String(rightResizeStartWidth.current));
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

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

  const companies = roomList.filter(
    (r) =>
      !r.is_direct &&
      !r.is_group &&
      (!search ||
        r.name.toLowerCase().includes(search.toLowerCase()) ||
        (r.description || '').toLowerCase().includes(search.toLowerCase()))
  );

  const groups = roomList.filter(
    (r) =>
      !r.is_direct &&
      r.is_group &&
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

  const handleCompanyContextMenu = (e, room) => {
    e.preventDefault();
    e.stopPropagation();
    setCompanyContextMenu({
      x: e.clientX,
      y: e.clientY,
      room,
    });
  };

  useEffect(() => {
    if (!companyContextMenu) return;
    const handleClick = () => setCompanyContextMenu(null);
    const handleEscape = (e) => {
      if (e.key === 'Escape') setCompanyContextMenu(null);
    };
    document.addEventListener('click', handleClick);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('click', handleClick);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [companyContextMenu]);

  const openChannelModalForRoom = (room) => {
    if (!room) return;
    setPendingChannelRoom(room);
    setChannelForm({ name: '', description: '' });
    setChannelError(null);
    setShowChannelModal(true);
    setCompanyContextMenu(null);
  };

  const handleCreateChannel = async (e) => {
    e.preventDefault();
    if (!pendingChannelRoom) return;
    setChannelError(null);
    const name = (channelForm.name || '').trim();
    const description = (channelForm.description || '').trim();
    if (!name) {
      setChannelError('Channel name is required');
      return;
    }
    try {
      const { data } = await rooms.channels.create(pendingChannelRoom.id, { name, description });
      window.dispatchEvent(
        new CustomEvent('channel-created', {
          detail: {
            roomId: pendingChannelRoom.id,
            channel: data,
          },
        })
      );
      setShowChannelModal(false);
      setPendingChannelRoom(null);
      setChannelForm({ name: '', description: '' });
    } catch (err) {
      const d = err.response?.data;
      const msg =
        d?.error ??
        d?.name?.[0] ??
        d?.description?.[0] ??
        d?.detail ??
        err.message ??
        'Failed to create channel';
      setChannelError(typeof msg === 'string' ? msg : String(msg));
    }
  };

  const toggleSelectGroupUser = (id) => {
    setSelectedGroupUserIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const filteredGroupUsers = userList.filter((u) => {
    if (!groupSearch) return true;
    const q = groupSearch.toLowerCase();
    return (
      (u.username || '').toLowerCase().includes(q) ||
      (u.first_name || '').toLowerCase().includes(q) ||
      (u.last_name || '').toLowerCase().includes(q)
    );
  });

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    setGroupError(null);
    const name = (newGroup.name || '').trim();
    const description = (newGroup.description || '').trim();
    if (!name) {
      setGroupError('Group name is required');
      return;
    }
    try {
      const payload = { name, description, is_group: true };
      const res = await rooms.create(payload);
      const data = res.data;
      const invitedIds = Array.from(selectedGroupUserIds);
      if (invitedIds.length) {
        try {
          await rooms.invite(data.id, invitedIds);
        } catch {
          // Ignore invite errors; group room still created
        }
      }
      setRoomList((prev) => [data, ...prev]);
      setNewGroup({ name: '', description: '' });
      setSelectedGroupUserIds(new Set());
      setGroupSearch('');
      setShowCreateGroupModal(false);
      navigate(`/company/${data.id}`);
    } catch (err) {
      const d = err.response?.data;
      const msg =
        d?.name?.[0] ??
        d?.description?.[0] ??
        d?.detail ??
        err.message ??
        'Failed to create group';
      setGroupError(typeof msg === 'string' ? msg : String(msg));
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
    <div className="main-layout" style={{ '--sidebar-width': `${sidebarWidth}px`, '--right-sidebar-width': `${rightSidebarWidth}px` }}>
      <div className="sidebar-wrapper">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-actions">
          <button className="sidebar-close-mobile" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar">
            <XIcon size={20} />
          </button>
          <div className="sidebar-brand-row">
            <div className="sidebar-actions-brand">
              <button
                className="sidebar-brand-btn"
                onClick={() => setShowActionMenu(!showActionMenu)}
                aria-label="Open menu"
                aria-expanded={showActionMenu}
              >
                <img src="/trutim.png" alt="Trutim" className="sidebar-brand-icon" />
              </button>
              {showActionMenu && (
              <>
                <div className="sidebar-action-menu-backdrop" onClick={() => setShowActionMenu(false)} aria-hidden />
                <div className="sidebar-action-menu">
                  <button
                    className="sidebar-action-btn"
                    onClick={() => { setShowCreateModal(true); setCreateError(null); setNewRoom({ name: '', description: '', avatar: null }); setShowActionMenu(false); }}
                    title="Create company"
                  >
                    <PlusIcon size={20} />
                    <span>Create company</span>
                  </button>
                  <button
                    className="sidebar-action-btn"
                    onClick={() => { setShowCreateGroupModal(true); setGroupError(null); setNewGroup({ name: '', description: '' }); setSelectedGroupUserIds(new Set()); setGroupSearch(''); setShowActionMenu(false); }}
                    title="Create group"
                  >
                    <PlusIcon size={20} />
                    <span>Create group</span>
                  </button>
                  <button
                    className="sidebar-action-btn"
                    onClick={() => { setShowActionMenu(false); }}
                    title="Blocked list"
                  >
                    <BanIcon size={20} />
                    <span>Blocked list</span>
                  </button>
                  <button
                    className="sidebar-action-btn"
                    onClick={() => { setShowActionMenu(false); }}
                    title="Archived"
                  >
                    <ArchiveIcon size={20} />
                    <span>Archived</span>
                  </button>
                  <button
                    className="sidebar-action-btn"
                    onClick={() => { setShowActionMenu(false); }}
                    title="Muted"
                  >
                    <BellOffIcon size={20} />
                    <span>Muted</span>
                  </button>
                  <button
                    className="sidebar-action-btn"
                    onClick={() => { navigate('/profile'); setShowActionMenu(false); }}
                    title="Settings"
                  >
                    <SettingsIcon size={20} />
                    <span>Settings</span>
                  </button>
                </div>
              </>
            )}
            </div>
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
          </div>
        </div>

        <div className="sidebar-list">
          {loading ? (
            <div className="sidebar-loading">Loading...</div>
          ) : (
            <>
              {companies.length > 0 && (
                <div className="sidebar-section">
                  <div className="section-label">Companies</div>
                  <ul className="item-list">
                    {companies.map((room) => (
                      <li
                        key={room.id}
                        onContextMenu={(e) => handleCompanyContextMenu(e, room)}
                      >
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
              {groups.length > 0 && (
                <div className="sidebar-section">
                  <div className="section-label">Groups</div>
                  <ul className="item-list">
                    {groups.map((room) => (
                      <li
                        key={room.id}
                        onContextMenu={(e) => handleCompanyContextMenu(e, room)}
                      >
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
                            <Avatar user={{ ...u, status: liveStatus }} size={36} />
                            <span className="item-name">{u.username}</span>
                          </NavLink>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
              {!loading && companies.length === 0 && groups.length === 0 && filteredUsers.length === 0 && (
                <div className="sidebar-empty">
                  {search ? 'No results found' : 'No companies or contacts yet'}
                </div>
              )}
            </>
          )}
        </div>
      </aside>
      <div
        className="sidebar-resize-handle"
        onMouseDown={handleResizeStart}
        title="Drag to resize sidebar"
        aria-label="Resize sidebar"
      />
      </div>
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
                <div className="right-sidebar-wrapper">
                  <div
                    className="right-sidebar-resize-handle"
                    onMouseDown={handleRightResizeStart}
                    title="Drag to resize sidebar"
                    aria-label="Resize sidebar"
                  />
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
                </div>
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

      {companyContextMenu && (
        <div
          className="company-context-menu"
          style={{ left: companyContextMenu.x, top: companyContextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            className="company-context-item"
            onClick={() => openChannelModalForRoom(companyContextMenu.room)}
          >
            <HashIcon size={16} className="company-context-icon" />
            <span>Create channel</span>
          </button>
        </div>
      )}

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

      {showChannelModal && (
        <div className="modal-overlay" onClick={() => setShowChannelModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create Channel</h2>
            <form onSubmit={handleCreateChannel}>
              {channelError && <p className="create-error">{channelError}</p>}
              <input
                placeholder="Channel name"
                value={channelForm.name}
                onChange={(e) => setChannelForm((prev) => ({ ...prev, name: e.target.value }))}
                required
                autoFocus
              />
              <input
                placeholder="Description (optional)"
                value={channelForm.description}
                onChange={(e) => setChannelForm((prev) => ({ ...prev, description: e.target.value }))}
              />
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Create</button>
                <button
                  type="button"
                  onClick={() => setShowChannelModal(false)}
                  className="btn-outline"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showCreateGroupModal && (
        <div className="modal-overlay" onClick={() => setShowCreateGroupModal(false)}>
          <div className="modal-content modal-content-large" onClick={(e) => e.stopPropagation()}>
            <h2>Create Group</h2>
            <form onSubmit={handleCreateGroup} className="create-group-form">
              {groupError && <p className="create-error">{groupError}</p>}
              <input
                placeholder="Group name"
                value={newGroup.name}
                onChange={(e) => setNewGroup((prev) => ({ ...prev, name: e.target.value }))}
                required
                autoFocus
              />
              <input
                placeholder="Description (optional)"
                value={newGroup.description}
                onChange={(e) => setNewGroup((prev) => ({ ...prev, description: e.target.value }))}
              />
              <div className="create-group-invite-section">
                <div className="create-group-invite-header">
                  <span>Invite people (optional)</span>
                  <input
                    type="text"
                    placeholder="Search people to invite..."
                    value={groupSearch}
                    onChange={(e) => setGroupSearch(e.target.value)}
                  />
                </div>
                <div className="create-group-user-list">
                  {filteredGroupUsers.map((u) => {
                    const selected = selectedGroupUserIds.has(u.id);
                    const liveStatus = getPresenceStatus(u.id) ?? u.status ?? 'deactive';
                    return (
                      <button
                        key={u.id}
                        type="button"
                        className={`create-group-user-item ${selected ? 'selected' : ''}`}
                        onClick={() => toggleSelectGroupUser(u.id)}
                      >
                        <Avatar user={{ ...u, status: liveStatus }} size={32} />
                        <span className="create-group-user-name">{u.username}</span>
                        {selected && <span className="create-group-user-selected-indicator">Added</span>}
                      </button>
                    );
                  })}
                  {filteredGroupUsers.length === 0 && (
                    <div className="create-group-empty">No people match your search</div>
                  )}
                </div>
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Create group</button>
                <button
                  type="button"
                  onClick={() => setShowCreateGroupModal(false)}
                  className="btn-outline"
                >
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
