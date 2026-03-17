import { useState, useRef, useCallback, useEffect } from 'react';
import EmojiPicker from './EmojiPicker';
import { FileIcon, LinkIcon, TypeIcon, SmileIcon, SendArrowIcon, CalendarIcon, ImageIcon } from './icons';
import AIImageModal from './AIImageModal';
import { markdownToHtml, htmlToMarkdown } from '../utils/richInput';
import './MessageInput.css';

const FONT_SIZES = [
  { label: 'S', value: 'small', wrap: '<small>', wrapEnd: '</small>' },
  { label: 'M', value: 'normal', wrap: '', wrapEnd: '' },
  { label: 'L', value: 'large', wrap: '<big>', wrapEnd: '</big>' },
];

function saveSelection() {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return null;
  return sel.getRangeAt(0).cloneRange();
}

function restoreSelection(savedRange) {
  if (!savedRange) return;
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(savedRange);
}

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
  const [showAIImageModal, setShowAIImageModal] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [linkText, setLinkText] = useState('');
  const [calendarTitle, setCalendarTitle] = useState('');
  const [calendarDate, setCalendarDate] = useState('');
  const [calendarTime, setCalendarTime] = useState('');
  const [calendarLocation, setCalendarLocation] = useState('');
  const editorRef = useRef(null);
  const emojiAnchorRef = useRef(null);
  const fileInputRef = useRef(null);
  const typingDebounceRef = useRef(null);
  const savedRangeRef = useRef(null);
  const isInternalUpdateRef = useRef(false);

  const keepFocus = (e) => e.preventDefault();

  const syncToMarkdown = useCallback(() => {
    const el = editorRef.current;
    if (!el) return;
    const html = el.innerHTML;
    const md = htmlToMarkdown(html);
    if (!isInternalUpdateRef.current && md !== (value || '')) {
      onChange(md);
    }
  }, [onChange, value]);

  useEffect(() => {
    if (isInternalUpdateRef.current) {
      isInternalUpdateRef.current = false;
      return;
    }
    const el = editorRef.current;
    if (!el) return;
    const md = value || '';
    const currentMd = htmlToMarkdown(el.innerHTML);
    if (currentMd !== md) {
      el.innerHTML = markdownToHtml(md) || '';
    }
  }, [value]);

  const notifyTyping = useCallback(() => {
    if (typingDebounceRef.current) clearTimeout(typingDebounceRef.current);
    onTyping?.({ typing: true });
    typingDebounceRef.current = setTimeout(() => {
      onTyping?.({ typing: false });
    }, 2000);
  }, [onTyping]);

  const wrapSelection = (before, after) => {
    const el = editorRef.current;
    if (!el) return;
    el.focus();
    const sel = window.getSelection();
    if (sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    const selected = range.toString();
    const wrapper = document.createElement('span');
    wrapper.innerHTML = before + selected + after;
    range.extractContents();
    range.insertNode(wrapper);
    range.setStartAfter(wrapper);
    range.setEndAfter(wrapper);
    sel.removeAllRanges();
    sel.addRange(range);
    syncToMarkdown();
  };

  const openLinkModal = () => {
    savedRangeRef.current = saveSelection();
    const sel = window.getSelection();
    const selectedText = sel?.rangeCount > 0 ? sel.toString() : '';
    setLinkText(selectedText);
    setLinkUrl('');
    setShowLinkModal(true);
  };

  const insertLink = () => {
    if (!linkUrl.trim()) return;
    const text = linkText.trim() || linkUrl.trim();
    const el = editorRef.current;
    if (!el) return;
    el.focus();
    restoreSelection(savedRangeRef.current);
    const sel = window.getSelection();
    const range = sel?.rangeCount > 0 ? sel.getRangeAt(0) : null;
    const a = document.createElement('a');
    a.href = linkUrl.trim();
    a.textContent = text;
    if (range) {
      range.deleteContents();
      range.insertNode(a);
      range.setStartAfter(a);
      range.setEndAfter(a);
      sel.removeAllRanges();
      sel.addRange(range);
    } else {
      el.appendChild(a);
    }
    setLinkUrl('');
    setLinkText('');
    setShowLinkModal(false);
    savedRangeRef.current = null;
    syncToMarkdown();
  };

  const openCalendarModal = () => {
    savedRangeRef.current = saveSelection();
    const sel = window.getSelection();
    const selectedText = sel?.rangeCount > 0 ? sel.toString() : '';
    setCalendarTitle(selectedText);
    setCalendarDate(new Date().toISOString().slice(0, 10));
    setCalendarTime('09:00');
    setCalendarLocation('');
    setShowCalendarModal(true);
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

  const insertCalendarLink = () => {
    const title = calendarTitle.trim() || 'Event';
    const dateStr = calendarDate || new Date().toISOString().slice(0, 10);
    const timeStr = calendarTime || '09:00';
    const location = calendarLocation.trim();
    const url = buildGoogleCalendarUrl(title, dateStr, timeStr, location);
    const linkText = `${title} - ${dateStr} ${timeStr}`;
    const el = editorRef.current;
    if (el) {
      el.focus();
      restoreSelection(savedRangeRef.current);
      const sel = window.getSelection();
      const range = sel?.rangeCount > 0 ? sel.getRangeAt(0) : null;
      const a = document.createElement('a');
      a.href = url;
      a.className = 'msg-input-date';
      a.textContent = `📅 ${linkText}`;
      if (range) {
        range.deleteContents();
        range.insertNode(a);
        range.setStartAfter(a);
        range.setEndAfter(a);
        sel.removeAllRanges();
        sel.addRange(range);
      } else {
        el.appendChild(a);
      }
    }
    setCalendarTitle('');
    setCalendarDate('');
    setCalendarTime('');
    setCalendarLocation('');
    setShowCalendarModal(false);
    savedRangeRef.current = null;
    syncToMarkdown();
  };

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (!files?.length) return;
    const el = editorRef.current;
    if (!el) return;
    el.focus();
    const sel = window.getSelection();
    const range = sel?.rangeCount > 0 ? sel.getRangeAt(0) : null;
    for (const file of files) {
      let url = '#';
      let text = file.name;
      if (onFileUpload) {
        try {
          const { data } = await onFileUpload(file);
          url = data.url || data;
          text = `📎 ${data.filename || file.name}`;
        } catch (err) {
          text = `📎 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        }
      } else {
        text = `📎 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      }
      const a = document.createElement('a');
      a.href = url;
      a.textContent = text;
      if (range) {
        range.insertNode(a);
        range.setStartAfter(a);
        range.setEndAfter(a);
        sel.removeAllRanges();
        sel.addRange(range);
      } else {
        el.appendChild(a);
      }
    }
    syncToMarkdown();
    e.target.value = '';
  };

  const addEmoji = (emoji) => {
    const el = editorRef.current;
    if (!el) return;
    el.focus();
    const sel = window.getSelection();
    const range = sel?.rangeCount > 0 ? sel.getRangeAt(0) : null;
    const text = document.createTextNode(emoji);
    if (range) {
      range.insertNode(text);
      range.setStartAfter(text);
      range.setEndAfter(text);
    } else {
      el.appendChild(text);
    }
    syncToMarkdown();
    setShowEmoji(false);
  };

  const handleFontSize = (fs) => {
    if (fs.wrap) wrapSelection(fs.wrap, fs.wrapEnd);
    setShowFontSize(false);
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    const el = editorRef.current;
    if (!el) return;
    const md = htmlToMarkdown(el.innerHTML);
    const text = md.trim();
    if (!text) return;
    onSend?.(text);
    isInternalUpdateRef.current = true;
    onChange('');
    el.innerHTML = '';
    onTyping?.({ typing: false });
  };

  const handleInput = () => {
    notifyTyping();
    syncToMarkdown();
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const text = e.clipboardData?.getData('text/plain') || '';
    document.execCommand('insertText', false, text);
  };

  const hasContent = ((value || '').trim().length > 0);

  return (
    <div className="message-input-container">
      <form onSubmit={handleSubmit} className="message-input-form">
        {(replyTo || isEditing) && (
          <div className="message-context-bar">
            <div className="message-context-main">
              <span className="message-context-label">
                {isEditing ? 'Editing' : 'Reply'}
              </span>
              {!isEditing && replyTo && (
                <>
                  <span className="message-context-target">
                    {replyTo.sender?.username || 'Message'}
                  </span>
                  {replyTo.content && (
                    <span className="message-context-snippet">
                      {replyTo.content.replace(/\s+/g, ' ').slice(0, 80)}
                    </span>
                  )}
                </>
              )}
              {isEditing && (
                <span className="message-context-snippet">
                  {(value || '').replace(/\s+/g, ' ').slice(0, 80)}
                </span>
              )}
            </div>
            <button
              type="button"
              className="message-context-cancel"
              onClick={isEditing ? onCancelEdit : onCancelReply}
              aria-label={isEditing ? 'Cancel editing' : 'Cancel reply'}
            >
              ×
            </button>
          </div>
        )}
        {showToolbar && (
          <div className="message-toolbar-inline">
            <button type="button" onMouseDown={keepFocus} onClick={() => fileInputRef.current?.click()} className="toolbar-btn" title="Attach file">
              <FileIcon size={18} />
            </button>
            <input ref={fileInputRef} type="file" multiple className="file-input-hidden" onChange={handleFileSelect} />
            <button type="button" onMouseDown={keepFocus} onClick={() => setShowAIImageModal(true)} className="toolbar-btn" title="AI Generate Image">
              <ImageIcon size={18} />
            </button>
            <button type="button" onMouseDown={keepFocus} onClick={openLinkModal} className="toolbar-btn" title="Insert link">
              <LinkIcon size={18} />
            </button>
            <button type="button" onMouseDown={keepFocus} onClick={openCalendarModal} className="toolbar-btn" title="Create calendar link">
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
          </div>
        )}
        <div className="input-wrapper">
          <div
            ref={editorRef}
            contentEditable={!disabled}
            suppressContentEditableWarning
            onInput={handleInput}
            onPaste={handlePaste}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            className="message-editor"
            data-placeholder={placeholder}
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
          <button type="submit" disabled={disabled || !hasContent} className="btn-send" title="Send (Enter)">
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
              <button type="button" onClick={insertCalendarLink}>Insert</button>
            </div>
          </div>
        </div>
      )}

      {showAIImageModal && (
        <AIImageModal
          onClose={() => setShowAIImageModal(false)}
          onSend={(text) => {
            onSend?.(text);
            setShowAIImageModal(false);
          }}
          theme={theme}
        />
      )}

    </div>
  );
}
