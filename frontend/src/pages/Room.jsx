import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { rooms, messages } from '../api';
import { useChatSocket } from '../hooks/useChatSocket';
import MessageInput from '../components/MessageInput';
import VideoCall from '../components/VideoCall';
import Avatar from '../components/Avatar';
import { VideoIcon, ArrowLeftIcon } from '../components/icons';
import '../components/Avatar.css';
import './Room.css';

export default function Room({ type = 'company' }) {
  const { id, userId } = useParams();
  const navigate = useNavigate();
  const roomIdParam = type === 'company' ? id : null;
  const contactUserId = type === 'contact' ? userId : null;
  const { user } = useAuth();
  const { theme } = useTheme();
  const token = localStorage.getItem('access');
  const [room, setRoom] = useState(null);
  const [msgList, setMsgList] = useState([]);
  const [input, setInput] = useState('');
  const [presence, setPresence] = useState([]);
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [showVideoCall, setShowVideoCall] = useState(false);
  const messagesEndRef = useRef(null);

  const effectiveRoomId = room?.id;

  useEffect(() => {
    if (roomIdParam) {
      rooms.get(roomIdParam)
        .then(({ data }) => setRoom(data))
        .catch(() => navigate('/'));
    } else if (contactUserId) {
      rooms.dm(contactUserId)
        .then(({ data }) => setRoom(data))
        .catch(() => navigate('/'));
    }
  }, [roomIdParam, contactUserId, navigate]);

  useEffect(() => {
    if (room) {
      messages.list(room.id).then(({ data }) => setMsgList(data));
    }
  }, [room]);

  const handleSocketMessage = (data) => {
    if (data.type === 'message') {
      setMsgList((prev) => [...prev, data.message]);
    } else if (data.type === 'typing') {
      setTypingUsers((prev) => {
        const next = new Set(prev);
        if (data.typing) next.add(data.user?.username);
        else next.delete(data.user?.username);
        return next;
      });
    } else if (data.type === 'user_joined') {
      setPresence((prev) => {
        const exists = prev.some((u) => u?.id === data.user?.id);
        return exists ? prev : [...prev.filter((u) => u?.id !== data.user?.id), data.user];
      });
    } else if (data.type === 'user_left') {
      setPresence((prev) => prev.filter((u) => u?.id !== data.user?.id));
    }
  };

  const { connected, send } = useChatSocket(effectiveRoomId, token, handleSocketMessage);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [msgList]);

  const sendMessage = useCallback((text) => {
    if (!text?.trim()) return;
    send({ type: 'message', content: text.trim() });
    send({ type: 'typing', typing: false });
  }, [send]);

  const handleTyping = useCallback(({ typing }) => {
    send({ type: 'typing', typing: !!typing });
  }, [send]);

  const quickEmojis = ['👍', '❤️', '😂', '🔥', '👏', '🚀', '💯', '✨'];

  const addReaction = async (msgId, emoji) => {
    try {
      const { data } = await messages.react(msgId, emoji);
      setMsgList((prev) => prev.map((m) => (m.id === msgId ? data : m)));
    } catch (err) {
      console.error(err);
    }
  };

  if (!room) return <div className="room-loading">Loading...</div>;

  return (
    <div className="room-page" key={effectiveRoomId}>
      {showVideoCall && (
        <VideoCall
          roomId={effectiveRoomId}
          token={token}
          user={user}
          onClose={() => setShowVideoCall(false)}
        />
      )}

      <header className="room-header">
        <button onClick={() => navigate('/')} className="btn-back">
          <ArrowLeftIcon size={18} /> Back
        </button>
        <div className="room-title">
          <h1>{type === 'contact' && room.dm_user ? room.dm_user.username : room.name}</h1>
          <span className={`status ${connected ? 'online' : ''}`}>
            {connected ? '● Live' : '○ Connecting...'}
          </span>
          {presence.length > 0 && (
            <span className="presence-count" title={presence.map((u) => u.username).join(', ')}>
              {presence.length} online
            </span>
          )}
        </div>
        <div className="room-actions">
          <button onClick={() => setShowVideoCall(true)} className="btn-icon" title="Video call">
            <VideoIcon size={20} />
          </button>
        </div>
      </header>

      <div className="room-content">
        <div className="messages-panel">
          <div className="messages-list">
            {msgList.map((msg) => (
              <div key={msg.id} className={`message ${msg.sender?.id === user?.id ? 'own' : ''}`}>
                <div className="message-header">
                  <Avatar user={msg.sender} size={28} showStatus={false} />
                  <strong>{msg.sender?.username}</strong>
                  {msg.sender?.title && <span className="msg-title">{msg.sender.title}</span>}
                  <span className="msg-time">
                    {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div className="message-body">{msg.content}</div>
                <div className="message-reactions">
                  {msg.reactions && Object.entries(msg.reactions).map(([emoji, ids]) => (
                    <button key={emoji} className="reaction" onClick={() => addReaction(msg.id, emoji)} title="Toggle reaction">
                      {emoji} {ids.length}
                    </button>
                  ))}
                  <span className="reaction-add" title="Add reaction">
                    {quickEmojis.slice(0, 5).map((e) => (
                      <button key={e} onClick={() => addReaction(msg.id, e)} className="reaction-btn">{e}</button>
                    ))}
                  </span>
                </div>
              </div>
            ))}
            {typingUsers.size > 0 && (
              <div className="typing-indicator">
                {[...typingUsers].join(', ')} typing...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <MessageInput
            value={input}
            onChange={setInput}
            onSend={sendMessage}
            onTyping={handleTyping}
            disabled={!connected}
            placeholder="Type a message..."
            showToolbar={true}
            quickEmojis={quickEmojis}
            onFileUpload={messages.upload}
            theme={theme}
          />
        </div>
      </div>
    </div>
  );
}
