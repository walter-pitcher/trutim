import { useState, useRef, useEffect, useCallback } from 'react';
import { useCallSocket } from '../hooks/useCallSocket';
import { XIcon } from './icons';
import { getUserMedia, getDisplayMedia, getMediaErrorMessage } from '../utils/mediaDevices';
import './VideoCall.css';

const ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
];

function RemoteVideo({ stream, displayName }) {
  const videoRef = useRef(null);
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = stream || null;
    }
  }, [stream]);
  return (
    <div className="vc-remote-tile">
      <video ref={videoRef} autoPlay playsInline style={{ display: stream ? 'block' : 'none' }} />
      {!stream && (
        <div className="vc-connecting">
          <span className="vc-connecting-spinner" />
          <span>Connecting...</span>
        </div>
      )}
      <span className="vc-tile-label">{displayName || 'Participant'}</span>
    </div>
  );
}

export default function VideoCall({ roomId, token, user, onClose }) {
  const [peers, setPeers] = useState({});
  const [localStream, setLocalStream] = useState(null);
  const [screenStream, setScreenStream] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [mediaError, setMediaError] = useState(null);
  const localVideoRef = useRef(null);
  const pcRef = useRef({});
  const localStreamRef = useRef(null);
  const screenStreamRef = useRef(null);
  localStreamRef.current = localStream;
  screenStreamRef.current = screenStream;

  const sendRef = useRef(null);

  const createPeerConnection = useCallback((peerId, isInitiator) => {
    if (pcRef.current[peerId]) return pcRef.current[peerId];
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    pcRef.current[peerId] = pc;

    pc.ontrack = (e) => {
      if (e.streams && e.streams[0]) {
        setPeers((prev) => ({
          ...prev,
          [peerId]: { ...prev[peerId], stream: e.streams[0], username: prev[peerId]?.username },
        }));
      }
    };

    pc.onicecandidate = (e) => {
      if (e.candidate && sendRef.current) {
        sendRef.current({
          type: 'ice-candidate',
          candidate: e.candidate.toJSON ? e.candidate.toJSON() : e.candidate,
          to_user: peerId,
        });
      }
    };

    return pc;
  }, []);

  const handleSignal = useCallback(async (data) => {
    const { type, from_user, offer, answer, candidate, to_user } = data;
    const peerId = from_user?.id;
    if (!peerId || peerId === user?.id) return;

    const shouldCreateOffer = user?.id != null && peerId != null && user.id < peerId;

    if (type === 'join') {
      if (!shouldCreateOffer) return;
      setPeers((prev) => ({ ...prev, [peerId]: { ...prev[peerId], username: from_user?.username } }));
      const stream = localStream || (await getUserMedia({ video: true, audio: true }));
      if (!localStream) setLocalStream(stream);
      const pc = createPeerConnection(peerId, true);
      const videoTrack = (screenStream || localStream)?.getVideoTracks()[0];
      const audioTrack = stream.getAudioTracks()[0];
      if (videoTrack) pc.addTrack(videoTrack, screenStream || stream);
      if (audioTrack) pc.addTrack(audioTrack, stream);
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      sendRef.current?.({ type: 'offer', offer, to_user: peerId });
    } else if (type === 'offer' && to_user === user?.id) {
      setPeers((prev) => ({ ...prev, [peerId]: { ...prev[peerId], username: from_user?.username } }));
      const pc = createPeerConnection(peerId, false);
      const stream = localStream || (await getUserMedia({ video: true, audio: true }));
      if (!localStream) setLocalStream(stream);
      const videoTrack = (screenStream || localStream)?.getVideoTracks()[0];
      const audioTrack = stream.getAudioTracks()[0];
      if (videoTrack) pc.addTrack(videoTrack, screenStream || stream);
      if (audioTrack) pc.addTrack(audioTrack, stream);
      await pc.setRemoteDescription(new RTCSessionDescription(offer));
      const ans = await pc.createAnswer();
      await pc.setLocalDescription(ans);
      sendRef.current?.({ type: 'answer', answer: ans, to_user: peerId });
    } else if (type === 'answer' && to_user === user?.id) {
      const pc = pcRef.current[peerId];
      if (pc) await pc.setRemoteDescription(new RTCSessionDescription(answer));
    } else if (type === 'ice-candidate' && candidate && to_user === user?.id) {
      const pc = pcRef.current[peerId];
      if (pc) {
        try {
          await pc.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (err) {
          console.warn('ICE candidate error:', err);
        }
      }
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
  }, [user?.id, localStream, screenStream, createPeerConnection]);

  const { send, connected } = useCallSocket(roomId, token, handleSignal);
  sendRef.current = send;

  useEffect(() => {
    const start = async () => {
      try {
        setMediaError(null);
        const stream = await getUserMedia({ video: true, audio: true });
        setLocalStream(stream);
      } catch (err) {
        console.error('Media error:', err);
        setMediaError(getMediaErrorMessage(err));
      }
    };
    start();
    return () => {
      localStreamRef.current?.getTracks().forEach((t) => t.stop());
      screenStreamRef.current?.getTracks().forEach((t) => t.stop());
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
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = isScreenSharing && screenStream ? screenStream : localStream;
    }
  }, [localStream, screenStream, isScreenSharing]);

  useEffect(() => {
    if (!localStream) return;
    const videoTrack = isScreenSharing && screenStream
      ? screenStream.getVideoTracks()[0]
      : localStream.getVideoTracks()[0];
    if (!videoTrack) return;
    Object.entries(pcRef.current).forEach(([, pc]) => {
      const sender = pc.getSenders().find((s) => s.track?.kind === 'video');
      if (sender) sender.replaceTrack(videoTrack);
    });
  }, [localStream, screenStream, isScreenSharing]);

  const toggleMute = () => {
    localStream?.getAudioTracks().forEach((t) => (t.enabled = !isMuted));
    setIsMuted(!isMuted);
  };

  const toggleVideo = () => {
    localStream?.getVideoTracks().forEach((t) => (t.enabled = !isVideoOff));
    setIsVideoOff(!isVideoOff);
  };

  const startScreenShare = async () => {
    try {
      const stream = await getDisplayMedia({ video: true });
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
    pcRef.current = {};
    onClose?.();
  };

  const peerList = Object.entries(peers);
  const hasPeers = peerList.length > 0;

  return (
    <div className="vc-overlay">
      <div className="vc-container">
        <header className="vc-header">
          <div className="vc-header-left">
            <span className={`vc-status-dot ${connected ? 'connected' : ''}`} />
            <h2 className="vc-title">Video Call</h2>
            {hasPeers && (
              <span className="vc-participant-count">{peerList.length} participant{peerList.length !== 1 ? 's' : ''}</span>
            )}
          </div>
          <button type="button" onClick={onClose} className="vc-close-btn" aria-label="Close">
            <XIcon size={20} />
          </button>
        </header>

        <div className="vc-main">
          {mediaError && (
            <div className="vc-error-banner">
              <span>{mediaError}</span>
            </div>
          )}

          <div className="vc-video-area">
            {hasPeers ? (
              <div className={`vc-grid ${peerList.length === 1 ? 'single' : ''}`}>
                {peerList.map(([id, p]) => (
                  <RemoteVideo key={id} stream={p.stream} displayName={p.username} />
                ))}
              </div>
            ) : (
              <div className="vc-waiting">
                <div className="vc-waiting-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="m22 8-6 4 6 4V8Z" />
                    <rect width="14" height="12" x="2" y="6" rx="2" />
                  </svg>
                </div>
                <h3>Waiting for others to join</h3>
                <p>Share this room link to invite participants. They'll appear here when they join.</p>
                {connected && <span className="vc-waiting-status">Connected</span>}
              </div>
            )}

            <div className="vc-local-preview">
              <video ref={localVideoRef} autoPlay muted playsInline />
              <span className="vc-tile-label">You</span>
              {isVideoOff && <div className="vc-video-off-overlay">Camera off</div>}
            </div>
          </div>

          <div className="vc-controls">
            <button
              type="button"
              onClick={toggleMute}
              className={`vc-ctrl-btn ${isMuted ? 'active' : ''}`}
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3Z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" x2="12" y1="19" y2="22" />
                  <line x1="5" x2="19" y1="22" y2="22" />
                  <line x1="2" x2="22" y1="2" y2="22" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3Z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" x2="12" y1="19" y2="22" />
                  <line x1="8" x2="16" y1="22" y2="22" />
                </svg>
              )}
              <span>{isMuted ? 'Unmute' : 'Mute'}</span>
            </button>

            <button
              type="button"
              onClick={toggleVideo}
              className={`vc-ctrl-btn ${isVideoOff ? 'active' : ''}`}
              title={isVideoOff ? 'Turn on camera' : 'Turn off camera'}
            >
              {isVideoOff ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m5.66 0H14a2 2 0 0 0 2-2V3a2 2 0 1 1 4 0v14a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-3" />
                  <line x1="2" x2="22" y1="2" y2="22" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="m22 8-6 4 6 4V8Z" />
                  <rect width="14" height="12" x="2" y="6" rx="2" ry="2" />
                </svg>
              )}
              <span>{isVideoOff ? 'Start' : 'Stop'} video</span>
            </button>

            <button
              type="button"
              onClick={isScreenSharing ? stopScreenShare : startScreenShare}
              className={`vc-ctrl-btn ${isScreenSharing ? 'active' : ''}`}
              title={isScreenSharing ? 'Stop sharing' : 'Share screen'}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect width="20" height="14" x="2" y="3" rx="2" />
                <path d="M8 21h8" />
                <path d="M12 17v4" />
              </svg>
              <span>{isScreenSharing ? 'Stop share' : 'Share screen'}</span>
            </button>

            <button
              type="button"
              onClick={hangUp}
              className="vc-ctrl-btn vc-hangup"
              title="End call"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
              </svg>
              <span>End call</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
