import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'trutim_user_status';
const DEFAULT_STATUS = 'active';
const DEFAULT_EMOJI = '😊';
const IDLE_MS = 5 * 60 * 1000; // 5 min no activity → idle

const UserStatusContext = createContext(null);

export function UserStatusProvider({ children }) {
  const [status, setStatusState] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const parsed = stored ? JSON.parse(stored) : { type: DEFAULT_STATUS, emoji: DEFAULT_EMOJI };
      return { ...parsed, manualOverride: parsed.manualOverride ?? false };
    } catch {
      return { type: DEFAULT_STATUS, emoji: DEFAULT_EMOJI, manualOverride: false };
    }
  });

  const [autoStatus, setAutoStatus] = useState(DEFAULT_STATUS);

  useEffect(() => {
    const toStore = { type: status.type, emoji: status.emoji, manualOverride: status.manualOverride };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
  }, [status]);

  const setStatus = (type, emoji) => {
    setStatusState((prev) => ({
      type: type ?? prev.type,
      emoji: emoji ?? prev.emoji,
      manualOverride: true,
    }));
  };

  const setStatusEmoji = (emoji) => setStatusState((prev) => ({ ...prev, emoji }));
  const setStatusType = (type) => setStatusState((prev) => ({ ...prev, type, manualOverride: true }));
  const setAuto = useCallback(() => setStatusState((prev) => ({ ...prev, manualOverride: false })), []);

  useEffect(() => {
    let idleTimer = null;

    const updateAuto = () => {
      const visible = document.visibilityState === 'visible';
      if (!visible) {
        setAutoStatus('idle');
        return;
      }
      setAutoStatus('active');
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        setAutoStatus('idle');
      } else {
        setAutoStatus('active');
      }
    };

    const resetIdle = () => {
      if (document.visibilityState !== 'visible') return;
      setAutoStatus('active');
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(() => setAutoStatus('idle'), IDLE_MS);
    };

    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('mousemove', resetIdle);
    window.addEventListener('keydown', resetIdle);
    window.addEventListener('mousedown', resetIdle);
    window.addEventListener('scroll', resetIdle);

    updateAuto();
    resetIdle();

    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('mousemove', resetIdle);
      window.removeEventListener('keydown', resetIdle);
      window.removeEventListener('mousedown', resetIdle);
      window.removeEventListener('scroll', resetIdle);
      if (idleTimer) clearTimeout(idleTimer);
    };
  }, []);

  const effectiveType = status.manualOverride ? status.type : autoStatus;

  return (
    <UserStatusContext.Provider
      value={{
        status: { ...status, type: effectiveType },
        setStatus,
        setStatusEmoji,
        setStatusType,
        setAuto,
        manualOverride: status.manualOverride,
      }}
    >
      {children}
    </UserStatusContext.Provider>
  );
}

export function useUserStatus() {
  const ctx = useContext(UserStatusContext);
  if (!ctx) throw new Error('useUserStatus must be used within UserStatusProvider');
  return ctx;
}
