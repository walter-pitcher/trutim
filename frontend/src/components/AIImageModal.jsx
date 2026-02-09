import { useState } from 'react';
import { ai } from '../api';
import { ImageIcon, XIcon } from './icons';
import './AIImageModal.css';

export default function AIImageModal({ onClose, onSend, theme = 'light' }) {
  const [prompt, setPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);

  const handleGenerate = async () => {
    const p = prompt.trim();
    if (!p) return;
    setError(null);
    setPreviewUrl(null);
    setGenerating(true);
    try {
      const { data } = await ai.generateImage(p);
      setPreviewUrl(data.url);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to generate image');
    } finally {
      setGenerating(false);
    }
  };

  const handleSend = () => {
    if (previewUrl) {
      const caption = prompt.trim() ? `🖼️ ${prompt.trim()}` : '🖼️ AI Generated Image';
      onSend?.(`![${caption}](${previewUrl})`);
      onClose?.();
    }
  };

  const handleClose = () => {
    setPrompt('');
    setError(null);
    setPreviewUrl(null);
    onClose?.();
  };

  return (
    <div className="ai-image-modal-overlay" onClick={handleClose}>
      <div className="ai-image-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ai-image-modal-header">
          <div className="ai-image-modal-title">
            <ImageIcon size={20} />
            <span>AI Image Generate</span>
          </div>
          <button type="button" onClick={handleClose} className="ai-image-modal-close" title="Close">
            <XIcon size={18} />
          </button>
        </div>

        <div className="ai-image-modal-body">
          <label className="ai-image-label">Describe the image you want</label>
          <textarea
            className="ai-image-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. A sunset over mountains with a lake in the foreground"
            rows={3}
            disabled={generating}
          />

          {error && (
            <div className="ai-image-error">{error}</div>
          )}

          {previewUrl && (
            <div className="ai-image-preview-wrap">
              <img src={previewUrl} alt="Generated" className="ai-image-preview" />
            </div>
          )}
        </div>

        <div className="ai-image-modal-actions">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={generating || !prompt.trim()}
            className="ai-image-btn ai-image-btn-generate"
          >
            {generating ? (
              <>
                <span className="ai-image-spinner" />
                Generating...
              </>
            ) : (
              'Generate'
            )}
          </button>
          {previewUrl && (
            <button
              type="button"
              onClick={handleSend}
              className="ai-image-btn ai-image-btn-send"
            >
              Send to Chat
            </button>
          )}
          <button type="button" onClick={handleClose} className="ai-image-btn ai-image-btn-cancel">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
