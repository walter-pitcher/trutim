import { useState, useRef, useEffect, useCallback } from 'react';
import { useCallSocket } from '../hooks/useCallSocket';

const ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
];

export default function VideoCall({ roomId, token, user, onClose }) {
  const [peers, setPeers] = useState({});
  const [localStream, setLocalStream] = useState(null);
  const [screenStream, setScreenStream] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const localVideoRef = useRef(null);
  const pcRef = useRef({});

  const sendRef = useRef(null);

  const createPeerConnection = useCallback((peerId, isInitiator) => {
    if (pcRef.current[peerId]) return pcRef.current[peerId];
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    pcRef.current[peerId] = pc;

    pc.ontrack = (e) => {
      setPeers((prev) => ({
        ...prev,
        [peerId]: { ...prev[peerId], stream: e.streams[0] },
      }));
    };

    pc.onicecandidate = (e) => {
      if (e.candidate && sendRef.current) {
        sendRef.current({ type: 'ice-candidate', candidate: e.candidate, to_user: peerId });
      }
    };

    return pc;
  }, []);

  const handleSignal = useCallback(async (data) => {
    const { type, from_user, offer, answer, candidate, to_user } = data;
    const peerId = from_user?.id;
    if (!peerId || peerId === user?.id) return;

    if (type === 'join') {
      const stream = localStream || (await navigator.mediaDevices.getUserMedia({ video: true, audio: true }));
      if (!localStream) setLocalStream(stream);
      const pc = createPeerConnection(peerId, true);
      stream.getTracks().forEach((t) => pc.addTrack(t, stream));
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      sendRef.current?.({ type: 'offer', offer, to_user: peerId });
    } else if (type === 'offer' && to_user === user?.id) {
      const pc = createPeerConnection(peerId, false);
      const stream = localStream || (await navigator.mediaDevices.getUserMedia({ video: true, audio: true }));
      if (!localStream) setLocalStream(stream);
      stream.getTracks().forEach((t) => pc.addTrack(t, stream));
      await pc.setRemoteDescription(new RTCSessionDescription(offer));
      const ans = await pc.createAnswer();
      await pc.setLocalDescription(ans);
      sendRef.current?.({ type: 'answer', answer: ans, to_user: peerId });
    } else if (type === 'answer' && to_user === user?.id) {
      const pc = pcRef.current[peerId];
      if (pc) await pc.setRemoteDescription(new RTCSessionDescription(answer));
    } else if (type === 'ice-candidate' && candidate && to_user === user?.id) {
      const pc = pcRef.current[peerId];
      if (pc) await pc.addIceCandidate(new RTCIceCandidate(candidate));
    } else if (type === 'user_left') {
      const pid = data.user_id;
      if (pcRef.current[pid]) {
        pcRef.current[pid].close();
        delete pcRef.current[pid];
      }
      setPeers((prev) => {
        const next = { ...prev };
        delete next[pid];
        return next;
      });
    }
  }, [user?.id, localStream, createPeerConnection]);

  const { send, connected } = useCallSocket(roomId, token, handleSignal);
  sendRef.current = send;

  useEffect(() => {
    const start = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        setLocalStream(stream);
      } catch (err) {
        console.error('Media error:', err);
      }
    };
    start();
    return () => {
      localStream?.getTracks().forEach((t) => t.stop());
      screenStream?.getTracks().forEach((t) => t.stop());
      Object.values(pcRef.current).forEach((pc) => pc.close());
      pcRef.current = {};
    };
  }, []);

  const joinSentRef = useRef(false);
  useEffect(() => {
    if (connected && localStream && !joinSentRef.current) {
      joinSentRef.current = true;
      send({ type: 'join' });
    }
  }, [connected, localStream, send]);

  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  const toggleMute = () => {
    localStream?.getAudioTracks().forEach((t) => (t.enabled = isMuted));
    setIsMuted(!isMuted);
  };

  const toggleVideo = () => {
    localStream?.getVideoTracks().forEach((t) => (t.enabled = isVideoOff));
    setIsVideoOff(!isVideoOff);
  };

  const startScreenShare = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      setScreenStream(stream);
      setIsScreenSharing(true);
      stream.getVideoTracks()[0].onended = () => {
        stream.getTracks().forEach((t) => t.stop());
        setScreenStream(null);
        setIsScreenSharing(false);
      };
    } catch (err) {
      console.error('Screen share failed:', err);
    }
  };

  const stopScreenShare = () => {
    screenStream?.getTracks().forEach((t) => t.stop());
    setScreenStream(null);
    setIsScreenSharing(false);
  };

  const hangUp = () => {
    localStream?.getTracks().forEach((t) => t.stop());
    screenStream?.getTracks().forEach((t) => t.stop());
    Object.values(pcRef.current).forEach((pc) => pc.close());
    onClose?.();
  };

  return (
    <div className="video-call-overlay">
      <div className="video-call-container">
        <div className="video-call-header">
          <h3>Video Call</h3>
          <button onClick={onClose} className="btn-close">×</button>
        </div>
        <div className="video-grid">
          <div className="video-tile local">
            <video ref={localVideoRef} autoPlay muted playsInline />
            <span className="video-label">You</span>
          </div>
          {Object.entries(peers).map(([id, p]) => (
            <div key={id} className="video-tile">
              <video autoPlay playsInline ref={(el) => el && (el.srcObject = p.stream)} />
              <span className="video-label">Peer</span>
            </div>
          ))}
        </div>
        <div className="video-controls">
          <button onClick={toggleMute} className={isMuted ? 'active' : ''} title={isMuted ? 'Unmute' : 'Mute'}>🎤</button>
          <button onClick={toggleVideo} className={isVideoOff ? 'active' : ''} title="Camera">📹</button>
          <button onClick={isScreenSharing ? stopScreenShare : startScreenShare} className={isScreenSharing ? 'active' : ''} title="Screen share">🖥️</button>
          <button onClick={hangUp} className="btn-hangup" title="End call">📞</button>
        </div>
      </div>
    </div>
  );
}
