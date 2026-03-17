import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext';
import { useUserStatus } from './UserStatusContext';

const getWsUrl = (path) => {
  const base = window.location.origin.replace(/^http/, 'ws');
  return `${base}${path}`;
};

const PresenceContext = createContext(null);

export function PresenceProvider({ children }) {
  const { user } = useAuth();
  const { status: userStatus } = useUserStatus();
  const [presence, setPresence] = useState({});
  const wsRef = useRef(null);
  const tokenRef = useRef(null);

  const sendStatus = useCallback((status) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'status', status }));
    }
  }, []);

  useEffect(() => {
    if (!user?.id) return;

    const token = localStorage.getItem('access');
    if (!token) return;

    tokenRef.current = token;
    const url = `${getWsUrl('/ws/presence/')}?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      sendStatus(userStatus.type);
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'presence_snapshot' && data.presence) {
          const next = {};
          for (const [uid, info] of Object.entries(data.presence)) {
            next[uid] = info.online ? (info.status || 'active') : 'deactive';
          }
          setPresence((prev) => ({ ...prev, ...next }));
        } else if (data.type === 'presence_update') {
          const { user_id, status, online } = data;
          setPresence((prev) => ({
            ...prev,
            [String(user_id)]: online ? (status || 'active') : 'deactive',
          }));
        }
      } catch (_) {}
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [user?.id]);

  // Sync local status to presence server when it changes (e.g. visibility, manual override)
  useEffect(() => {
    if (user?.id && wsRef.current?.readyState === WebSocket.OPEN) {
      sendStatus(userStatus.type);
    }
  }, [user?.id, userStatus.type, sendStatus]);

  const getStatus = useCallback(
    (userId) => {
      if (!userId) return undefined;
      return presence[String(userId)];
    },
    [presence]
  );

  return (
    <PresenceContext.Provider value={{ presence, getStatus }}>
      {children}
    </PresenceContext.Provider>
  );
}

export function usePresence() {
  const ctx = useContext(PresenceContext);
  if (!ctx) throw new Error('usePresence must be used within PresenceProvider');
  return ctx;
}
