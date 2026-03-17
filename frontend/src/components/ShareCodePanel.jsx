import { useState } from 'react';
import { CodeIcon, XIcon, SendArrowIcon } from './icons';
import './ShareCodePanel.css';

const LANGUAGES = [
  { value: '', label: 'Plain' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'python', label: 'Python' },
  { value: 'java', label: 'Java' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'json', label: 'JSON' },
  { value: 'sql', label: 'SQL' },
  { value: 'bash', label: 'Bash' },
  { value: 'git', label: 'Git' },
];

export default function ShareCodePanel({ isOpen, onClose, onShare }) {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('');

  const handleShare = () => {
    const trimmed = code.trim();
    if (!trimmed) return;
    const langTag = language ? language : '';
    const formatted = `\`\`\`${langTag}\n${trimmed}\n\`\`\``;
    onShare?.(formatted);
    setCode('');
    setLanguage('');
    onClose?.();
  };

  const handleClose = () => {
    setCode('');
    setLanguage('');
    onClose?.();
  };

  if (!isOpen) return null;

  return (
    <div className="share-code-overlay" onClick={handleClose}>
      <div className="share-code-panel" onClick={(e) => e.stopPropagation()}>
        <div className="share-code-header">
          <div className="share-code-title">
            <CodeIcon size={20} />
            <span>Share Code</span>
          </div>
          <button type="button" onClick={handleClose} className="share-code-close" title="Close">
            <XIcon size={18} />
          </button>
        </div>

        <div className="share-code-body">
          <label className="share-code-label">Paste your code</label>
          <div className="share-code-language-row">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="share-code-language"
            >
              {LANGUAGES.map((opt) => (
                <option key={opt.value || 'plain'} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <textarea
            className="share-code-input"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste or type your code here..."
            spellCheck={false}
          />
          <div className="share-code-preview">
            <div className="share-code-preview-label">Preview</div>
            <pre className="share-code-preview-block">
              <code>{code || '(empty)'}</code>
            </pre>
          </div>
        </div>

        <div className="share-code-actions">
          <button
            type="button"
            onClick={handleShare}
            disabled={!code.trim()}
            className="share-code-btn share-code-btn-send"
          >
            <SendArrowIcon size={16} />
            Share to Chat
          </button>
          <button type="button" onClick={handleClose} className="share-code-btn share-code-btn-cancel">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
