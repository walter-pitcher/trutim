import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { rooms, messages } from '../api';
import { useChatSocket } from '../hooks/useChatSocket';
import { notifyNewMessage, requestPermission } from '../utils/notify';
import MessageInput from '../components/MessageInput';
import VideoCall from '../components/VideoCall';
import Avatar from '../components/Avatar';
import DecorativeSvg from '../components/DecorativeSvg';
import { VideoIcon, ArrowLeftIcon, ReplyIcon, EditIcon, TrashIcon, CheckIcon, CheckDoubleIcon } from '../components/icons';

function formatDateLabel(date) {
  const d = new Date(date);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: d.getFullYear() !== today.getFullYear() ? 'numeric' : undefined });
}
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
  const [replyTo, setReplyTo] = useState(null);
  const [editingMessage, setEditingMessage] = useState(null);
  const messagesEndRef = useRef(null);
  const messagesStartRef = useRef(null);
  const prevMsgCountRef = useRef(0);

  const effectiveRoomId = room?.id;

  useEffect(() => {
    requestPermission();
  }, []);

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
    const handler = (e) => {
      if (e.detail?.id === room?.id) setRoom(e.detail);
    };
    window.addEventListener('company-updated', handler);
    return () => window.removeEventListener('company-updated', handler);
  }, [room?.id]);

  useEffect(() => {
    if (room) {
      messages.list(room.id).then(({ data }) => {
        const sorted = [...(data || [])].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        setMsgList(sorted);
      });
    }
  }, [room]);

  const handleSocketMessage = (data) => {
    if (data.type === 'message') {
      const msg = data.message;
      const isFromOthers = msg?.sender?.id !== user?.id;
      if (isFromOthers) {
        notifyNewMessage(msg.sender?.username || 'Someone', msg.content, type === 'contact' && room?.dm_user ? room.dm_user.username : room?.name || 'Chat');
      }
      setMsgList((prev) => {
        const withNew = { ...msg, isNew: true };
        return [...prev.filter((m) => m.id !== msg.id), withNew];
      });
      window.dispatchEvent(new CustomEvent('room-activity', { detail: { roomId: room?.id, type, contactUserId } }));
    } else if (data.type === 'message_updated' || data.type === 'message_edited') {
      if (data.message) {
        setMsgList((prev) => prev.map((m) => (m.id === data.message.id ? { ...data.message, isNew: m.isNew } : m)));
      }
    } else if (data.type === 'message_deleted') {
      const deletedId = data.message_id ?? data.id ?? data.message?.id;
      if (deletedId) {
        setMsgList((prev) => prev.filter((m) => m.id !== deletedId));
      }
    } else if (data.type === 'typing') {
      if (data.user?.id === user?.id) return; // Don't show typing state for self (only on receiver side)
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
    } else if (data.type === 'message_read') {
      const ids = data.message_ids || [];
      const readerId = data.user?.id;
      if (ids.length && readerId) {
        setMsgList((prev) =>
          prev.map((m) => {
            if (!ids.includes(m.id)) return m;
            const readBy = m.read_by || [];
            if (readBy.includes(readerId)) return m;
            return { ...m, read_by: [...readBy, readerId] };
          })
        );
      }
    }
  };

  const { connected, send } = useChatSocket(effectiveRoomId, token, handleSocketMessage);
  const markReadPendingRef = useRef(new Set());
  const markReadTimerRef = useRef(null);

  const flushMarkRead = useCallback(() => {
    if (markReadPendingRef.current.size === 0 || !effectiveRoomId) return;
    const ids = [...markReadPendingRef.current];
    markReadPendingRef.current.clear();
    if (connected) {
      send({ type: 'message_read', message_ids: ids });
    } else {
      messages.markRead(effectiveRoomId, ids).catch(() => {});
    }
  }, [effectiveRoomId, connected, send]);

  const scheduleMarkRead = useCallback(
    (msgId) => {
      if (!msgId || !user?.id) return;
      markReadPendingRef.current.add(msgId);
      if (markReadTimerRef.current) clearTimeout(markReadTimerRef.current);
      markReadTimerRef.current = setTimeout(flushMarkRead, 400);
    },
    [flushMarkRead, user?.id]
  );

  useEffect(() => {
    if (!room?.id || !user?.id) return;
    msgList.forEach((msg) => {
      const alreadyRead = (msg.read_by || []).includes(user.id);
      if (msg.sender?.id !== user.id && msg.id && !alreadyRead) {
        scheduleMarkRead(msg.id);
      }
    });
  }, [room?.id, user?.id, msgList, scheduleMarkRead]);

  useEffect(() => {
    return () => {
      if (markReadTimerRef.current) clearTimeout(markReadTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (msgList.length > prevMsgCountRef.current && prevMsgCountRef.current > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    } else if (msgList.length > 0 && prevMsgCountRef.current === 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
    }
    prevMsgCountRef.current = msgList.length;
  }, [msgList]);

  useEffect(() => {
    prevMsgCountRef.current = 0;
  }, [effectiveRoomId]);

  const newMsgIds = useMemo(() => msgList.filter((m) => m.isNew).map((m) => m.id), [msgList]);
  useEffect(() => {
    if (newMsgIds.length === 0) return;
    const timer = setTimeout(() => {
      setMsgList((prev) => prev.map((msg) => (msg.isNew ? { ...msg, isNew: false } : msg)));
    }, 5000);
    return () => clearTimeout(timer);
  }, [newMsgIds.join(',')]);

  const sendMessage = useCallback((text) => {
    if (!text?.trim()) return;

    const payload = {
      type: editingMessage ? 'edit' : 'message',
      content: text.trim(),
    };

    if (editingMessage) {
      payload.id = editingMessage.id;
    } else if (replyTo) {
      payload.parent = replyTo.id;
    }

    send(payload);
    send({ type: 'typing', typing: false });

    if (editingMessage) {
      setEditingMessage(null);
    }
    if (replyTo) {
      setReplyTo(null);
    }
  }, [send, replyTo, editingMessage]);

  const handleTyping = useCallback(({ typing }) => {
    send({ type: 'typing', typing: !!typing });
  }, [send]);

  const handleReply = useCallback((message) => {
    setReplyTo(message);
    setEditingMessage(null);
  }, []);

  const handleEdit = useCallback((message) => {
    setEditingMessage(message);
    setReplyTo(null);
    setInput(message.content || '');
  }, []);

  const handleDelete = useCallback((message) => {
    if (!message?.id) return;
    // Let the backend broadcast deletion to all clients
    send({ type: 'delete', id: message.id });
  }, [send]);

  const quickEmojis = ['👍', '❤️', '😂', '🔥', '👏', '🚀', '💯', '✨'];

  const messageItems = useMemo(() => {
    const items = [];
    let lastDate = null;
    let lastSenderId = null;

    msgList.forEach((msg) => {
      const msgDate = msg.created_at ? new Date(msg.created_at).toDateString() : null;
      const showDateSeparator = msgDate && msgDate !== lastDate;
      const isGrouped = msg.sender?.id === lastSenderId;

      if (showDateSeparator) {
        items.push({ type: 'date', date: msg.created_at });
        lastDate = msgDate;
      }
      items.push({ type: 'message', message: msg, isGrouped });
      lastSenderId = msg.sender?.id;
    });

    return items;
  }, [msgList]);

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
            {connected ? 'Live' : 'Connecting...'}
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
          <div className="messages-panel-decorative">
            <DecorativeSvg variant="compact" />
          </div>
          <div className="messages-list">
            <div ref={messagesStartRef} />
            {msgList.length === 0 && !typingUsers.size && (
              <div className="chat-empty-state">
                <div className="chat-empty-illustrations">
                  <svg className="chat-fun-svg chat-bubble-1" viewBox="0 0 200 200" aria-hidden>
                    <ellipse cx="100" cy="95" rx="70" ry="55" fill="var(--accent)" opacity="0.25" />
                    <path d="M55 95 Q55 140 100 140 Q145 140 145 95 Q145 50 100 50 Q55 50 55 95Z" fill="var(--accent)" opacity="0.4" />
                    <circle cx="75" cy="90" r="8" fill="var(--text-muted)" opacity="0.4" />
                    <circle cx="100" cy="90" r="8" fill="var(--text-muted)" opacity="0.4" />
                    <circle cx="125" cy="90" r="8" fill="var(--text-muted)" opacity="0.4" />
                    <path d="M85 115 Q100 130 115 115" stroke="var(--text-muted)" strokeWidth="4" fill="none" opacity="0.5" strokeLinecap="round" />
                  </svg>
                  <svg className="chat-fun-svg chat-bubble-2" viewBox="0 0 200 200" aria-hidden>
                    <path d="M40 80 Q40 50 80 50 L120 50 Q160 50 160 80 L160 120 Q160 150 120 150 L80 150 L60 170 Z" fill="var(--accent)" opacity="0.35" />
                    <circle cx="80" cy="95" r="12" fill="var(--accent)" opacity="0.5" />
                    <circle cx="120" cy="95" r="12" fill="var(--accent)" opacity="0.5" />
                    <path d="M70 125 Q100 145 130 125" stroke="var(--accent)" strokeWidth="6" fill="none" opacity="0.6" strokeLinecap="round" />
                  </svg>
                  <svg className="chat-fun-svg chat-sparkle" viewBox="0 0 200 200" aria-hidden>
                    <path d="M100 30 L108 90 L170 98 L108 106 L100 170 L92 106 L30 98 L92 90 Z" fill="#f59e0b" opacity="0.5" />
                    <path d="M100 50 L104 85 L140 89 L104 93 L100 130 L96 93 L60 89 L96 85 Z" fill="#fef3c7" opacity="0.7" />
                  </svg>
                </div>
                <h3>Every great conversation begins here</h3>
                <p>Your first message is waiting. Share code, links, or ideas—whatever moves you forward. Use the toolbar below for formatting and more.</p>
                <span className="chat-empty-hint">Press Enter to send · Shift+Enter for new line</span>
              </div>
            )}
            {messageItems.map((item, i) =>
              item.type === 'date' ? (
                <div key={`date-${item.date}-${i}`} className="date-separator">
                  <span>{formatDateLabel(item.date)}</span>
                </div>
              ) : (
                <div
                  key={item.message.id}
                  className={`message ${item.message.sender?.id === user?.id ? 'own' : ''} ${item.isGrouped ? 'grouped' : ''} ${item.message.isNew ? 'message-new' : ''}`}
                >
                  {!item.isGrouped && (
                    <div className="message-header">
                      <Avatar user={item.message.sender} size={28} showStatus={false} />
                      <strong>{item.message.sender?.username}</strong>
                      {item.message.isNew && <span className="message-badge-new">New</span>}
                      {item.message.sender?.title && <span className="msg-title">{item.message.sender.title}</span>}
                      <span className="msg-time" title={new Date(item.message.created_at).toLocaleString()}>
                        {new Date(item.message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  )}
                  {item.isGrouped && (
                    <span className="msg-time-grouped" title={new Date(item.message.created_at).toLocaleString()}>
                      {new Date(item.message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      {item.message.isNew && <span className="message-badge-new">New</span>}
                    </span>
                  )}
                  <div className="message-body">{item.message.content}</div>
                  <div className="message-footer">
                    <div className="message-reactions">
                      {item.message.reactions && Object.entries(item.message.reactions).map(([emoji, ids]) => (
                        <button
                          key={emoji}
                          className="reaction"
                          onClick={() => addReaction(item.message.id, emoji)}
                          title="Toggle reaction"
                        >
                          {emoji} {ids.length}
                        </button>
                      ))}
                      <span className="reaction-add" title="Add reaction">
                        {quickEmojis.slice(0, 5).map((e) => (
                          <button
                            key={e}
                            onClick={() => addReaction(item.message.id, e)}
                            className="reaction-btn"
                          >
                            {e}
                          </button>
                        ))}
                      </span>
                    </div>
                    <div className="message-actions">
                      {item.message.sender?.id === user?.id && (
                        <span className="msg-read-status" title={(item.message.read_by || []).length > 0 ? 'Seen by receiver' : 'Sent'}>
                          {(item.message.read_by || []).length > 0 ? (
                            <CheckDoubleIcon size={14} className="msg-read-seen" />
                          ) : (
                            <CheckIcon size={14} className="msg-read-sent" />
                          )}
                        </span>
                      )}
                      <button
                        type="button"
                        className="message-action-btn"
                        onClick={() => handleReply(item.message)}
                        title="Reply"
                      >
                        <ReplyIcon size={14} />
                        <span>Reply</span>
                      </button>
                      {item.message.sender?.id === user?.id && (
                        <>
                          <button
                            type="button"
                            className="message-action-btn"
                            onClick={() => handleEdit(item.message)}
                            title="Edit message"
                          >
                            <EditIcon size={14} />
                            <span>Edit</span>
                          </button>
                          <button
                            type="button"
                            className="message-action-btn message-action-danger"
                            onClick={() => handleDelete(item.message)}
                            title="Delete message"
                          >
                            <TrashIcon size={14} />
                            <span>Delete</span>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )
            )}
            {typingUsers.size > 0 && (
              <div className="typing-indicator">
                <span className="typing-dots">
                  <span></span><span></span><span></span>
                </span>
                <span className="typing-names">{[...typingUsers].join(', ')} typing</span>
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
            replyTo={replyTo}
            isEditing={!!editingMessage}
            onCancelReply={() => setReplyTo(null)}
            onCancelEdit={() => { setEditingMessage(null); setInput(''); }}
          />
        </div>
      </div>
    </div>
  );
}
