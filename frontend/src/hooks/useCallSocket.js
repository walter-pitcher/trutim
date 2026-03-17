import { useEffect, useRef, useState, useCallback } from 'react';

const getWsUrl = (path) => {
  const base = window.location.origin.replace(/^http/, 'ws');
  const apiBase = base;
  return `${apiBase}${path}`;
};

export function useCallSocket(roomId, token, onSignal) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    if (!roomId || !token) return;

    const url = `${getWsUrl(`/ws/call/${roomId}/`)}?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        onSignal?.(data);
      } catch (_) {}
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [roomId, token]);

  return { connected, send };
}
