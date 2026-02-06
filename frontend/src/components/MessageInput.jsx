import { useState, useRef, useCallback } from 'react';
import EmojiPicker from './EmojiPicker';
import { CodeIcon, FileIcon, LinkIcon, TypeIcon, SmileIcon, GitBranchIcon, SendArrowIcon, CalendarIcon } from './icons';
import './MessageInput.css';

const FONT_SIZES = [
  { label: 'S', value: 'small', wrap: '<small>', wrapEnd: '</small>' },
  { label: 'M', value: 'normal', wrap: '', wrapEnd: '' },
  { label: 'L', value: 'large', wrap: '<big>', wrapEnd: '</big>' },
];

export default function MessageInput({
  value,
  onChange,
  onSend,
  onTyping,
  disabled,
  placeholder = 'Type a message...',
  showToolbar = true,
  quickEmojis = ['👍', '❤️', '😂', '🔥', '👏', '🚀', '💯', '✨'],
  onFileUpload,
  theme = 'light',
  replyTo = null,
  isEditing = false,
  onCancelReply,
  onCancelEdit,
}) {
  const [showEmoji, setShowEmoji] = useState(false);
  const [showFontSize, setShowFontSize] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [showCalendarModal, setShowCalendarModal] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [linkText, setLinkText] = useState('');
  const [calendarTitle, setCalendarTitle] = useState('');
  const [calendarDate, setCalendarDate] = useState('');
  const [calendarTime, setCalendarTime] = useState('');
  const [calendarLocation, setCalendarLocation] = useState('');
  const textareaRef = useRef(null);
  const emojiAnchorRef = useRef(null);
  const fileInputRef = useRef(null);
  const typingDebounceRef = useRef(null);

  const keepFocus = (e) => e.preventDefault();

  const notifyTyping = useCallback(() => {
    if (typingDebounceRef.current) clearTimeout(typingDebounceRef.current);
    onTyping?.({ typing: true });
    typingDebounceRef.current = setTimeout(() => {
      onTyping?.({ typing: false });
    }, 2000);
  }, [onTyping]);

  const insertAtCursor = (before, after = '', textOverride) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const text = textOverride ?? value ?? '';
    const selected = text.slice(start, end);
    const newText = text.slice(0, start) + before + selected + after + text.slice(end);
    onChange(newText);
    setTimeout(() => {
      ta.focus();
      ta.setSelectionRange(start + before.length, start + before.length + selected.length);
    }, 0);
  };

  const insertCode = () => {
    insertAtCursor('```\n', '\n```');
    setShowFontSize(false);
  };

  const insertGitBlock = () => {
    insertAtCursor('```git\n', '\n```');
    setShowFontSize(false);
  };

  const insertLink = () => {
    if (linkUrl.trim()) {
      const text = linkText.trim() || linkUrl;
      insertAtCursor(`[${text}](${linkUrl.trim()})`, '');
      setLinkUrl('');
      setLinkText('');
      setShowLinkModal(false);
    }
  };

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (!files?.length) return;
    const ta = textareaRef.current;
    let currentText = ta?.value ?? value ?? '';
    let insertPos = ta?.selectionStart ?? currentText.length;
    for (const file of files) {
      let toInsert;
      if (onFileUpload) {
        try {
          const { data } = await onFileUpload(file);
          const url = data.url || data;
          const name = data.filename || file.name;
          toInsert = `[📎 ${name}](${url})`;
        } catch (err) {
          const name = file.name;
          const size = (file.size / 1024).toFixed(1);
          toInsert = `[📎 ${name} (${size} KB)]`;
        }
      } else {
        const name = file.name;
        const size = (file.size / 1024).toFixed(1);
        toInsert = `[📎 ${name} (${size} KB)]`;
      }
      currentText = currentText.slice(0, insertPos) + toInsert + currentText.slice(insertPos);
      insertPos += toInsert.length;
    }
    onChange(currentText);
    setTimeout(() => {
      ta?.focus();
      ta?.setSelectionRange(insertPos, insertPos);
    }, 0);
    e.target.value = '';
  };

  const addEmoji = (emoji) => {
    const ta = textareaRef.current;
    if (ta) {
      const start = ta.selectionStart;
      const text = value || '';
      const newText = text.slice(0, start) + emoji + text.slice(start);
      onChange(newText);
      setTimeout(() => ta.setSelectionRange(start + emoji.length, start + emoji.length), 0);
    }
    setShowEmoji(false);
  };

  const handleFontSize = (fs) => {
    if (fs.wrap) insertAtCursor(fs.wrap, fs.wrapEnd);
    setShowFontSize(false);
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    const text = (value || '').trim();
    if (!text) return;
    onSend?.(text);
    onChange('');
    onTyping?.({ typing: false });
  };

  const buildGoogleCalendarUrl = (title, dateStr, timeStr, location) => {
    const [year, month, day] = dateStr.split('-').map(Number);
    const [hours = 0, minutes = 0] = (timeStr || '00:00').split(':').map(Number);
    const start = new Date(year, month - 1, day, hours, minutes);
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    const format = (d) => d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
    const params = new URLSearchParams({
      action: 'TEMPLATE',
      text: title || 'Event',
      dates: `${format(start)}/${format(end)}`,
    });
    if (location) params.set('location', location);
    return `https://calendar.google.com/calendar/render?${params.toString()}`;
  };

  const handleCreateCalendarLink = () => {
    const title = calendarTitle.trim() || 'Event';
    const dateStr = calendarDate || new Date().toISOString().slice(0, 10);
    const timeStr = calendarTime || '09:00';
    const location = calendarLocation.trim();
    const url = buildGoogleCalendarUrl(title, dateStr, timeStr, location);
    const linkText = `${title} - ${dateStr} ${timeStr}`;
    const toSend = `[📅 ${linkText}](${url})`;
    onSend?.(toSend);
    setCalendarTitle('');
    setCalendarDate('');
    setCalendarTime('');
    setCalendarLocation('');
    setShowCalendarModal(false);
  };

  return (
    <div className="message-input-container">
      {(replyTo || isEditing) && (
        <div className="message-context-bar">
          <div className="message-context-main">
            <span className="message-context-label">
              {isEditing ? 'Editing message' : 'Replying to'}
            </span>
            {!isEditing && replyTo && (
              <span className="message-context-target">
                {replyTo.sender?.username || 'message'}
              </span>
            )}
            {!isEditing && replyTo?.content && (
              <span className="message-context-snippet">
                {replyTo.content.slice(0, 80)}
                {replyTo.content.length > 80 ? '…' : ''}
              </span>
            )}
          </div>
          <button
            type="button"
            className="message-context-cancel"
            onClick={isEditing ? onCancelEdit : onCancelReply}
            aria-label="Cancel reply or edit"
          >
            ×
          </button>
        </div>
      )}
      <form onSubmit={handleSubmit} className="message-input-form">
        {showToolbar && (
          <div className="message-toolbar-inline">
            <button type="button" onMouseDown={keepFocus} onClick={() => fileInputRef.current?.click()} className="toolbar-btn" title="Attach file">
              <FileIcon size={18} />
            </button>
            <input ref={fileInputRef} type="file" multiple className="file-input-hidden" onChange={handleFileSelect} />
            <button type="button" onMouseDown={keepFocus} onClick={insertCode} className="toolbar-btn" title="Code block">
              <CodeIcon size={18} />
            </button>
            <button type="button" onMouseDown={keepFocus} onClick={() => setShowLinkModal(true)} className="toolbar-btn" title="Insert link">
              <LinkIcon size={18} />
            </button>
            <button type="button" onMouseDown={keepFocus} onClick={() => setShowCalendarModal(true)} className="toolbar-btn" title="Create calendar link">
              <CalendarIcon size={18} />
            </button>
            <div className="toolbar-dropdown">
              <button type="button" onMouseDown={keepFocus} onClick={() => setShowFontSize(!showFontSize)} className="toolbar-btn" title="Format">
                <TypeIcon size={18} />
              </button>
              {showFontSize && (
                <>
                  <div className="toolbar-backdrop" onClick={() => setShowFontSize(false)} />
                  <div className="toolbar-menu">
                    {FONT_SIZES.map((fs) => (
                      <button key={fs.value} type="button" onMouseDown={keepFocus} onClick={() => handleFontSize(fs)}>
                        {fs.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
            <button ref={emojiAnchorRef} type="button" onMouseDown={keepFocus} onClick={() => setShowEmoji(!showEmoji)} className="toolbar-btn" title="Emoji">
              <SmileIcon size={18} />
            </button>
            <EmojiPicker onSelect={addEmoji} visible={showEmoji} onClose={() => setShowEmoji(false)} anchorRef={emojiAnchorRef} theme={theme} />
            <button type="button" onMouseDown={keepFocus} onClick={insertGitBlock} className="toolbar-btn" title="Git block">
              <GitBranchIcon size={18} />
            </button>
          </div>
        )}
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => { onChange(e.target.value); notifyTyping(); }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="message-textarea"
          />
        </div>
        <div className="message-input-actions">
          {showToolbar && (
            <div className="quick-emojis-inline">
              {quickEmojis.slice(0, 4).map((e) => (
                <button key={e} type="button" onMouseDown={keepFocus} onClick={() => addEmoji(e)} className="quick-emoji-btn" title={`Add ${e}`}>{e}</button>
              ))}
            </div>
          )}
          <button type="submit" disabled={disabled || !(value || '').trim()} className="btn-send" title="Send (Enter)">
            <SendArrowIcon size={20} />
          </button>
        </div>
      </form>

      {showLinkModal && (
        <div className="link-modal-overlay" onClick={() => setShowLinkModal(false)}>
          <div className="link-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Insert Link</h3>
            <input
              type="url"
              placeholder="URL"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              autoFocus
            />
            <input
              type="text"
              placeholder="Link text (optional)"
              value={linkText}
              onChange={(e) => setLinkText(e.target.value)}
            />
            <div className="link-modal-actions">
              <button type="button" onClick={() => setShowLinkModal(false)}>Cancel</button>
              <button type="button" onClick={insertLink} disabled={!linkUrl.trim()}>Insert</button>
            </div>
          </div>
        </div>
      )}

      {showCalendarModal && (
        <div className="link-modal-overlay" onClick={() => setShowCalendarModal(false)}>
          <div className="link-modal calendar-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Create Calendar Link</h3>
            <input
              type="text"
              placeholder="Event title"
              value={calendarTitle}
              onChange={(e) => setCalendarTitle(e.target.value)}
              autoFocus
            />
            <input
              type="date"
              value={calendarDate || new Date().toISOString().slice(0, 10)}
              onChange={(e) => setCalendarDate(e.target.value)}
            />
            <input
              type="time"
              value={calendarTime || '09:00'}
              onChange={(e) => setCalendarTime(e.target.value)}
            />
            <input
              type="text"
              placeholder="Location (optional)"
              value={calendarLocation}
              onChange={(e) => setCalendarLocation(e.target.value)}
            />
            <div className="link-modal-actions">
              <button type="button" onClick={() => setShowCalendarModal(false)}>Cancel</button>
              <button type="button" onClick={handleCreateCalendarLink}>Create & Send</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
