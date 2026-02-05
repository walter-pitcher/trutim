import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { rooms, messages } from '../api';
import { useChatSocket } from '../hooks/useChatSocket';
import EmojiPicker from '../components/EmojiPicker';
import VideoCall from '../components/VideoCall';
import './Room.css';

export default function Room() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const token = localStorage.getItem('access');
  const [room, setRoom] = useState(null);
  const [msgList, setMsgList] = useState([]);
  const [input, setInput] = useState('');
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [showEmoji, setShowEmoji] = useState(false);
  const [showVideoCall, setShowVideoCall] = useState(false);
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  useEffect(() => {
    rooms.get(id)
      .then(({ data }) => setRoom(data))
      .catch(() => navigate('/'));
  }, [id, navigate]);

  useEffect(() => {
    if (room) {
      messages.list(id).then(({ data }) => setMsgList(data));
    }
  }, [id, room]);

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
    }
  };

  const { connected, send } = useChatSocket(id, token, handleSocketMessage);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [msgList]);

  const sendMessage = (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text) return;
    send({ type: 'message', content: text });
    setInput('');
    send({ type: 'typing', typing: false });
  };

  const handleTyping = () => {
    send({ type: 'typing', typing: true });
    clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      send({ type: 'typing', typing: false });
    }, 2000);
  };

  const addEmoji = (emoji) => {
    setInput((prev) => prev + emoji);
    setShowEmoji(false);
  };

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
    <div className="room-page" key={id}>
      {showVideoCall && (
        <VideoCall
          roomId={id}
          token={token}
          user={user}
          onClose={() => setShowVideoCall(false)}
        />
      )}

      <header className="room-header">
        <button onClick={() => navigate('/')} className="btn-back">← Back</button>
        <div className="room-title">
          <h1>{room.name}</h1>
          <span className={`status ${connected ? 'online' : ''}`}>
            {connected ? '● Live' : '○ Connecting...'}
          </span>
        </div>
        <div className="room-actions">
          <button onClick={() => setShowVideoCall(true)} className="btn-icon" title="Video call">
            📹
          </button>
        </div>
      </header>

      <div className="room-content">
        <div className="messages-panel">
          <div className="messages-list">
            {msgList.map((msg) => (
              <div key={msg.id} className={`message ${msg.sender?.id === user?.id ? 'own' : ''}`}>
                <div className="message-header">
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

          <div className="quick-emojis">
            {quickEmojis.map((e) => (
              <button key={e} onClick={() => setInput((p) => p + e)} className="quick-emoji">{e}</button>
            ))}
          </div>

          <form onSubmit={sendMessage} className="message-form">
            <div className="input-wrapper">
              <input
                value={input}
                onChange={(e) => { setInput(e.target.value); handleTyping(); }}
                placeholder="Type a message..."
                disabled={!connected}
              />
              <button type="button" onClick={(e) => { e.stopPropagation(); setShowEmoji(!showEmoji); }} className="btn-emoji" title="Emoji">
                😀
              </button>
              <EmojiPicker onSelect={addEmoji} visible={showEmoji} onClose={() => setShowEmoji(false)} />
            </div>
            <button type="submit" disabled={!connected || !input.trim()} className="btn-send">
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
