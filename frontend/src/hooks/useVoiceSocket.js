import { useEffect, useRef, useState, useCallback } from 'react';
import { startVoiceCapture } from '../utils/voiceAudioCapture';

const getWsUrl = (path) => {
  const base = window.location.origin.replace(/^http/, 'ws');
  return `${base}${path}`;
};

// Voice control WebSocket hook
export function useVoiceSocket(roomId, token) {
  const [connected, setConnected] = useState(false);
  const [listening, setListening] = useState(false);
  const [detectorState, setDetectorState] = useState('IDLE');
  const [awaitingCommand, setAwaitingCommand] = useState(false);
  const [wakeConfidence, setWakeConfidence] = useState(0);
  const [lastEvent, setLastEvent] = useState(null);
  const [lastCommandResult, setLastCommandResult] = useState(null);

  const wsRef = useRef(null);
  const captureRef = useRef(null);

  const sendRaw = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const startListening = useCallback(() => {
    sendRaw({ type: 'start_listening' });
  }, [sendRaw]);

  const stopListening = useCallback(() => {
    sendRaw({ type: 'stop_listening' });
  }, [sendRaw]);

  const sendTextCommand = useCallback(
    (text, overrideRoomId) => {
      if (!text) return;
      sendRaw({ type: 'text_command', text, room_id: overrideRoomId ?? roomId ?? null });
    },
    [sendRaw, roomId]
  );

  const sendKeywordCommand = useCallback(
    (keywords, overrideRoomId) => {
      if (!keywords || !keywords.length) return;
      sendRaw({ type: 'keyword_command', keywords, room_id: overrideRoomId ?? roomId ?? null });
    },
    [sendRaw, roomId]
  );

  // Microphone capture: stream audio to backend when listening
  useEffect(() => {
    if (!listening || !connected) {
      captureRef.current?.stop?.();
      captureRef.current = null;
      return;
    }

    let cancelled = false;
    startVoiceCapture(sendRaw)
      .then((capture) => {
        if (cancelled) {
          capture.stop();
          return;
        }
        captureRef.current = capture;
      })
      .catch((err) => console.error('Voice capture failed:', err));

    return () => {
      cancelled = true;
      captureRef.current?.stop?.();
      captureRef.current = null;
    };
  }, [listening, connected, sendRaw]);

  useEffect(() => {
    if (!token) return;

    const path = roomId ? `/ws/voice/${roomId}/` : '/ws/voice/';
    const url = `${getWsUrl(path)}?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ type: 'get_status' }));
    };
    ws.onclose = () => {
      setConnected(false);
      setListening(false);
      setAwaitingCommand(false);
      setDetectorState('IDLE');
      captureRef.current?.stop?.();
      captureRef.current = null;
    };
    ws.onmessage = (e) => {
      let data;
      try {
        data = JSON.parse(e.data);
      } catch {
        return;
      }

      setLastEvent(data);

      if (data.type === 'listening_state') {
        setListening(data.state === 'listening');
        if (data.detector_state) setDetectorState(data.detector_state);
      } else if (data.type === 'wake_word_detected') {
        setWakeConfidence(data.confidence ?? 0);
        setAwaitingCommand(true);
      } else if (data.type === 'keyword_spotted') {
        setAwaitingCommand(true);
      } else if (data.type === 'status') {
        const st = data.data?.detector_state || data.data?.state;
        if (st) setDetectorState(st);
      } else if (data.type === 'command_result') {
        setLastCommandResult(data.result ?? null);
        setAwaitingCommand(false);
      } else if (data.type === 'command_timeout') {
        setAwaitingCommand(false);
      }
    };

    return () => {
      captureRef.current?.stop?.();
      captureRef.current = null;
      ws.close();
      wsRef.current = null;
    };
  }, [roomId, token]);

  return {
    connected,
    listening,
    detectorState,
    awaitingCommand,
    wakeConfidence,
    lastEvent,
    lastCommandResult,
    startListening,
    stopListening,
    sendTextCommand,
    sendKeywordCommand,
  };
}

