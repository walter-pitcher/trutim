import { useState, useCallback, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import mermaid from 'mermaid';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.min.css';
import { XIcon, CopyIcon, ExternalLinkIcon, CheckIcon } from './icons';
import { FlowDiagramView } from './DiagramModal';
import './MessageContent.css';

const CODE_BLOCK_COLLAPSE_LINES = 12;

function MermaidDiagram({ code, theme = 'light' }) {
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

  if (error) return <div className="msg-content-diagram-error">{error}</div>;
  if (!svg) return <div className="msg-content-diagram-loading">Loading diagram…</div>;
  return <div className="msg-content-mermaid" dangerouslySetInnerHTML={{ __html: svg }} />;
}

function CodeBlock({ code, lang, theme, codeIdx, onFontToggle, onExpandToggle, fontToggles, expandToggles }) {
  const useNormalFont = fontToggles[codeIdx];
  const isExpanded = expandToggles[codeIdx];
  const lines = code.split('\n');
  const isLong = lines.length > CODE_BLOCK_COLLAPSE_LINES;
  const showCollapsed = isLong && !isExpanded;
  const displayCode = showCollapsed ? lines.slice(0, CODE_BLOCK_COLLAPSE_LINES).join('\n') : code;

  const [copied, setCopied] = useState(false);
  const copyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [code]);

  let highlighted;
  try {
    if (lang && hljs.getLanguage(lang)) {
      highlighted = hljs.highlight(displayCode, { language: lang });
    } else {
      highlighted = hljs.highlightAuto(displayCode);
    }
  } catch {
    highlighted = { value: displayCode };
  }

  return (
    <div className="msg-content-code-wrap">
      <div className="msg-content-code-header">
        {lang && <span className="msg-content-code-lang">{lang}</span>}
        <div className="msg-content-code-actions">
          <button
            type="button"
            className={`msg-content-code-copy ${copied ? 'copied' : ''}`}
            onClick={copyToClipboard}
            title={copied ? 'Copied!' : 'Copy code'}
          >
            {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>
      <pre
        className={`msg-content-code-block hljs ${lang ? 'has-lang' : ''} ${useNormalFont ? 'font-normal' : ''} ${showCollapsed ? 'code-collapsed' : ''}`}
        onClick={(e) => { if (!e.target.closest('button')) onFontToggle(codeIdx); }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && !e.target.closest('button') && onFontToggle(codeIdx)}
        title="Click to toggle font style"
      >
        <code dangerouslySetInnerHTML={{ __html: highlighted.value }} />
        {showCollapsed && <span className="msg-content-code-fade" aria-hidden />}
      </pre>
      {isLong && (
        <button
          type="button"
          className="msg-content-code-expand"
          onClick={(e) => { e.stopPropagation(); onExpandToggle(codeIdx); }}
        >
          {isExpanded ? 'Show less' : `Show more (${lines.length - CODE_BLOCK_COLLAPSE_LINES} more lines)`}
        </button>
      )}
    </div>
  );
}

export default function MessageContent({ content, theme = 'light' }) {
  const [codeFontToggles, setCodeFontToggles] = useState({});
  const [codeExpanded, setCodeExpanded] = useState({});
  const [lightboxUrl, setLightboxUrl] = useState(null);
  const codeBlockIndexRef = useRef(0);

  const toggleCodeFont = useCallback((idx) => {
    setCodeFontToggles((prev) => ({ ...prev, [idx]: !prev[idx] }));
  }, []);

  const toggleCodeExpand = useCallback((idx) => {
    setCodeExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }));
  }, []);

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

  const getNextCodeIdx = useCallback(() => {
    const idx = codeBlockIndexRef.current;
    codeBlockIndexRef.current += 1;
    return idx;
  }, []);

  codeBlockIndexRef.current = 0;

  const components = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const lang = match ? match[1] : '';
      const code = String(children).replace(/\n$/, '');

      if (inline) {
        return <code className="msg-content-inline-code" {...props}>{children}</code>;
      }

      if (lang === 'mermaid') {
        return (
          <div className="msg-content-diagram-wrap">
            <MermaidDiagram code={code} theme={theme} />
          </div>
        );
      }

      if (lang === 'flowdiagram') {
        return (
          <div className="msg-content-diagram-wrap">
            <FlowDiagramView flowData={code} theme={theme} />
          </div>
        );
      }

      const idx = getNextCodeIdx();
      return (
        <CodeBlock
          key={idx}
          code={code}
          lang={lang}
          theme={theme}
          codeIdx={idx}
          onFontToggle={toggleCodeFont}
          onExpandToggle={toggleCodeExpand}
          fontToggles={codeFontToggles}
          expandToggles={codeExpanded}
        />
      );
    },
    img({ src, alt, ...props }) {
      const caption = alt && alt !== 'Image' && !alt.startsWith('🖼️') && alt !== '🖼️ AI Generated Image';
      return (
        <span className="msg-content-image-wrap">
          <div className="msg-content-image-card">
            <a
              href={src}
              target="_blank"
              rel="noopener noreferrer"
              className="msg-content-link msg-content-image-link"
              onClick={(e) => openLightbox(e, src)}
            >
              <img src={src} alt={alt || 'Image'} className="msg-content-image" loading="lazy" {...props} />
            </a>
            {caption && <span className="msg-content-caption">{alt}</span>}
          </div>
        </span>
      );
    },
    a({ href, children, ...props }) {
      const isExternal = href?.startsWith('http://') || href?.startsWith('https://');
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="msg-content-link msg-content-link-external" {...props}>
          {children}
          {isExternal && <ExternalLinkIcon className="msg-content-link-icon" size={14} />}
        </a>
      );
    },
    pre({ children, ...props }) {
      const child = Array.isArray(children) ? children[0] : children;
      const cn = child?.props?.className ?? '';
      const isCustomBlock = cn.includes('msg-content-code-wrap') || cn.includes('msg-content-diagram-wrap');
      return isCustomBlock ? <>{children}</> : <pre {...props}>{children}</pre>;
    },
  };

  if (!content || typeof content !== 'string') {
    return <div className="msg-content" />;
  }

  return (
    <div className="msg-content">
      <div className="msg-content-inner markdown-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
          {content}
        </ReactMarkdown>
      </div>
      {lightboxUrl && (
        <div
          className="msg-content-lightbox"
          onClick={closeLightbox}
          role="dialog"
          aria-modal="true"
          aria-label="Image preview"
        >
          <button type="button" className="msg-content-lightbox-close" onClick={closeLightbox} title="Close (Esc)">
            <XIcon size={24} />
          </button>
          <img
            src={lightboxUrl}
            alt=""
            className="msg-content-lightbox-image"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
