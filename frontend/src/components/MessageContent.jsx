import { useState, useCallback, useEffect, useRef } from 'react';
import mermaid from 'mermaid';
import { XIcon } from './icons';
import { FlowDiagramView } from './DiagramModal';

/**
 * Renders message content with support for:
 * - Markdown-style links and images [text](url), ![alt](url), ![alt|WxH](url)
 * - Code blocks ```language\ncode```
 * - Bold **text**, italic *text*, strikethrough ~~text~~
 */
function renderFormattedText(str) {
  if (!str || typeof str !== 'string') return str;
  const parts = [];
  let remaining = str;
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|~~[^~]+~~|`[^`]+`)/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: str.slice(lastIndex, match.index) });
    }
    const raw = match[1];
    if (raw.startsWith('**') && raw.endsWith('**')) {
      parts.push({ type: 'bold', value: raw.slice(2, -2) });
    } else if (raw.startsWith('*') && raw.endsWith('*') && raw.length > 2) {
      parts.push({ type: 'italic', value: raw.slice(1, -1) });
    } else if (raw.startsWith('~~') && raw.endsWith('~~')) {
      parts.push({ type: 'strike', value: raw.slice(2, -2) });
    } else if (raw.startsWith('`') && raw.endsWith('`')) {
      parts.push({ type: 'code', value: raw.slice(1, -1) });
    } else {
      parts.push({ type: 'text', value: raw });
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < str.length) {
    parts.push({ type: 'text', value: str.slice(lastIndex) });
  }
  return parts.length ? parts : [{ type: 'text', value: str }];
}
function parseContent(text) {
  if (!text || typeof text !== 'string') return [{ type: 'text', value: text || '' }];
  const parts = [];
  let remaining = text;

  // Process code blocks first (```...```)
  const codeBlockRegex = /```(\w*)\r?\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;
  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const before = text.slice(lastIndex, match.index);
      parts.push(...parseInlineContent(before));
    }
    parts.push({ type: 'code', lang: match[1] || '', value: match[2].trimEnd() });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(...parseInlineContent(text.slice(lastIndex)));
  }
  return parts.length ? parts : [{ type: 'text', value: text }];
}

function parseInlineContent(text) {
  const parts = [];
  // Match ![alt](url) for images OR [text](url) for links; capture optional ! and optional |WxH for image size
  const linkRegex = /(!)?\[([^\]]*)\]\(([^)]+)\)/g;
  let lastIndex = 0;
  let m;
  while ((m = linkRegex.exec(text)) !== null) {
    if (m.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, m.index) });
    }
    const isImageSyntax = !!m[1]; // ! prefix means markdown image
    let linkText = m[2];
    const url = m[3];
    let width, height;
    const sizeMatch = linkText.match(/\|(\d+)x(\d+)$/);
    if (sizeMatch) {
      width = parseInt(sizeMatch[1], 10);
      height = parseInt(sizeMatch[2], 10);
      linkText = linkText.replace(/\|\d+x\d+$/, '').trim() || 'Image';
    }
    const looksLikeImage = /\.(png|jpg|jpeg|gif|webp|svg)(\?|$)/i.test(url) ||
      url.startsWith('data:image/') ||
      url.includes('/media/') || url.includes('/ai_images/') || url.includes('message_uploads');
    const isImage = isImageSyntax || looksLikeImage;
    parts.push({ type: isImage ? 'image' : 'link', text: linkText, url, width, height });
    lastIndex = m.index + m[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) });
  }
  return parts.length ? parts : [{ type: 'text', value: text }];
}

const CODE_BLOCK_COLLAPSE_LINES = 12;

function MermaidDiagram({ code, theme = 'light' }) {
  const containerRef = useRef(null);
  const [svg, setSvg] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!code?.trim()) return;
    let cancelled = false;
    const id = 'mermaid-' + Math.random().toString(36).slice(2, 11);
    mermaid.initialize({
      startOnLoad: false,
      theme: theme === 'dark' ? 'dark' : 'default',
      securityLevel: 'loose',
    });
    mermaid.render(id, code.trim())
      .then(({ svg: s }) => {
        if (!cancelled) setSvg(s);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Diagram error');
      });
    return () => { cancelled = true; };
  }, [code, theme]);

  if (error) return <div className="message-content-mermaid-error">{error}</div>;
  if (!svg) return <div className="message-content-mermaid-loading">Loading diagram…</div>;
  return <div className="message-content-mermaid" dangerouslySetInnerHTML={{ __html: svg }} />;
}

export default function MessageContent({ content, theme = 'light' }) {
  const [codeFontToggles, setCodeFontToggles] = useState({});
  const [codeExpanded, setCodeExpanded] = useState({});
  const [lightboxUrl, setLightboxUrl] = useState(null);
  const parts = parseContent(content);

  const toggleCodeFont = (idx) => {
    setCodeFontToggles((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const toggleCodeExpand = (idx) => {
    setCodeExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const openLightbox = useCallback((e, url) => {
    e.preventDefault();
    e.stopPropagation();
    setLightboxUrl(url);
  }, []);

  const closeLightbox = useCallback(() => setLightboxUrl(null), []);

  useEffect(() => {
    if (!lightboxUrl) return;
    const handleEscape = (e) => e.key === 'Escape' && closeLightbox();
    document.addEventListener('keydown', handleEscape);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [lightboxUrl, closeLightbox]);

  return (
    <div className="message-content-inner">
      {parts.map((p, i) => {
        if (p.type === 'text') {
          const formatted = renderFormattedText(p.value);
          return (
            <span key={i}>
              {formatted.map((f, j) => {
                if (f.type === 'bold') return <strong key={j}>{f.value}</strong>;
                if (f.type === 'italic') return <em key={j}>{f.value}</em>;
                if (f.type === 'strike') return <del key={j}>{f.value}</del>;
                if (f.type === 'code') return <code key={j} className="message-content-inline-code">{f.value}</code>;
                return <span key={j}>{f.value}</span>;
              })}
            </span>
          );
        }
        if (p.type === 'code') {
          if (p.lang === 'mermaid') {
            return (
              <div key={i} className="message-content-mermaid-wrap">
                <MermaidDiagram code={p.value} theme={theme} />
              </div>
            );
          }
          if (p.lang === 'flowdiagram') {
            return (
              <div key={i} className="message-content-flowdiagram-wrap">
                <FlowDiagramView flowData={p.value} theme={theme} />
              </div>
            );
          }
          const useNormalFont = codeFontToggles[i];
          const lines = p.value.split('\n');
          const isLong = lines.length > CODE_BLOCK_COLLAPSE_LINES;
          const isExpanded = codeExpanded[i];
          const showCollapsed = isLong && !isExpanded;
          const displayValue = showCollapsed ? lines.slice(0, CODE_BLOCK_COLLAPSE_LINES).join('\n') : p.value;
          return (
            <div key={i} className="message-content-code-wrap">
              <pre
                className={`message-content-code-block ${p.lang ? 'has-lang' : ''} ${useNormalFont ? 'font-normal' : ''} ${showCollapsed ? 'message-content-code-collapsed' : ''}`}
                onClick={(e) => { if (!e.target.closest('.message-content-code-expand-btn')) toggleCodeFont(i); }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && !e.target.closest('.message-content-code-expand-btn') && toggleCodeFont(i)}
                title="Click to toggle font style"
              >
                {p.lang && <span className="message-content-code-lang">{p.lang}</span>}
                <code>{displayValue}</code>
                {showCollapsed && <span className="message-content-code-fade" aria-hidden />}
              </pre>
              {isLong && (
                <button
                  type="button"
                  className="message-content-code-expand-btn"
                  onClick={(e) => { e.stopPropagation(); toggleCodeExpand(i); }}
                >
                  {isExpanded ? 'Show less' : `Show more (${lines.length - CODE_BLOCK_COLLAPSE_LINES} more lines)`}
                </button>
              )}
            </div>
          );
        }
        if (p.type === 'image') {
          const imgStyle = {};
          if (p.width && p.height) {
            imgStyle.width = p.width;
            imgStyle.height = p.height;
            imgStyle.maxWidth = '100%';
            imgStyle.objectFit = 'contain';
          }
          return (
            <span key={i} className="message-content-image-wrap">
              <a
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="message-content-link message-content-image-link"
                onClick={(e) => openLightbox(e, p.url)}
              >
                <img src={p.url} alt={p.text || 'Image'} className="message-content-image" loading="lazy" style={imgStyle} />
              </a>
              {p.text && p.text !== '🖼️ AI Generated Image' && !p.text.startsWith('🖼️') && p.text !== 'Image' && (
                <span className="message-content-caption">{p.text}</span>
              )}
            </span>
          );
        }
        if (p.type === 'link') {
          return (
            <a key={i} href={p.url} target="_blank" rel="noopener noreferrer" className="message-content-link">
              {p.text}
            </a>
          );
        }
        return null;
      })}
      {lightboxUrl && (
        <div className="message-content-lightbox-overlay" onClick={closeLightbox} role="dialog" aria-modal="true" aria-label="Image preview">
          <button type="button" className="message-content-lightbox-close" onClick={closeLightbox} title="Close">
            <XIcon size={24} />
          </button>
          <img src={lightboxUrl} alt="" className="message-content-lightbox-image" onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </div>
  );
}
