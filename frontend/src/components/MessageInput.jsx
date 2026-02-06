import { useState, useRef, useCallback } from 'react';
import EmojiPicker from './EmojiPicker';
import { CodeIcon, FileIcon, LinkIcon, TypeIcon, SmileIcon, ImageIcon, GitBranchIcon } from './icons';
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
}) {
  const [showEmoji, setShowEmoji] = useState(false);
  const [showSticker, setShowSticker] = useState(false);
  const [showFontSize, setShowFontSize] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [linkText, setLinkText] = useState('');
  const textareaRef = useRef(null);
  const emojiAnchorRef = useRef(null);
  const fileInputRef = useRef(null);
  const typingDebounceRef = useRef(null);

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

  return (
    <div className="message-input-container">
      {showToolbar && (
        <div className="message-toolbar">
          <button type="button" onClick={insertCode} className="toolbar-btn" title="Code block">
            <CodeIcon size={18} />
          </button>
          <button type="button" onClick={() => fileInputRef.current?.click()} className="toolbar-btn" title="Upload file">
            <FileIcon size={18} />
          </button>
          <input ref={fileInputRef} type="file" multiple className="file-input-hidden" onChange={handleFileSelect} />
          <button type="button" onClick={() => setShowLinkModal(true)} className="toolbar-btn" title="Insert link">
            <LinkIcon size={18} />
          </button>
          <div className="toolbar-dropdown">
            <button type="button" onClick={() => setShowFontSize(!showFontSize)} className="toolbar-btn" title="Font size">
              <TypeIcon size={18} />
            </button>
            {showFontSize && (
              <>
                <div className="toolbar-backdrop" onClick={() => setShowFontSize(false)} />
                <div className="toolbar-menu">
                  {FONT_SIZES.map((fs) => (
                    <button key={fs.value} type="button" onClick={() => handleFontSize(fs)}>
                      {fs.label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
          <button ref={emojiAnchorRef} type="button" onClick={() => { setShowEmoji(!showEmoji); setShowSticker(false); }} className="toolbar-btn" title="Emoji">
            <SmileIcon size={18} />
          </button>
          <EmojiPicker onSelect={addEmoji} visible={showEmoji} onClose={() => setShowEmoji(false)} anchorRef={emojiAnchorRef} theme={theme} />
          <button type="button" onClick={() => { setShowSticker(!showSticker); setShowEmoji(false); }} className="toolbar-btn" title="Sticker">
            <ImageIcon size={18} />
          </button>
          {showSticker && (
            <div className="sticker-picker">
              <div className="sticker-grid">
                {['😀', '😎', '🤔', '😍', '🥳', '🤯', '👍', '👋', '🙌', '💪', '🔥', '⭐', '💯', '🚀', '✨', '❤️'].map((s) => (
                  <button key={s} type="button" onClick={() => { addEmoji(s); setShowSticker(false); }} className="sticker-btn">{s}</button>
                ))}
              </div>
            </div>
          )}
          <button type="button" onClick={insertGitBlock} className="toolbar-btn" title="Git block">
            <GitBranchIcon size={18} />
          </button>
        </div>
      )}

      <div className="quick-emojis-row">
        {quickEmojis.map((e) => (
          <button key={e} type="button" onClick={() => addEmoji(e)} className="quick-emoji-btn">{e}</button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="message-input-form">
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
        <button type="submit" disabled={disabled || !(value || '').trim()} className="btn-send">
          Send
        </button>
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
    </div>
  );
}
