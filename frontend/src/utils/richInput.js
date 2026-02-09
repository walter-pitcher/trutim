/**
 * Convert markdown-style content to HTML for contenteditable display
 */
export function markdownToHtml(md) {
  if (!md || typeof md !== 'string') return '';
  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks ```lang\n...\n```
  html = html.replace(/```(\w*)\r?\n([\s\S]*?)```/g, (_, lang, code) => {
    const codeEsc = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    if (lang === 'flowdiagram') {
      return `<span class="msg-input-flowdiagram" contenteditable="false" data-flowdiagram="${codeEsc}" title="Double-click to edit diagram">📊 Diagram</span>`;
    }
    return `<pre class="msg-input-code" data-lang="${lang || ''}"><code>${codeEsc}</code></pre>`;
  });

  // Images ![alt](url) - must come before links
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
    const altEsc = (alt || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const urlEsc = url.replace(/"/g, '&quot;');
    return `<img src="${urlEsc}" alt="${altEsc}" class="msg-input-img">`;
  });

  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, text, url) => {
    const textEsc = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const urlEsc = url.replace(/"/g, '&quot;');
    const isDate = text.startsWith('📅');
    return `<a href="${urlEsc}" ${isDate ? 'class="msg-input-date"' : ''}>${textEsc}</a>`;
  });

  return html.replace(/\n/g, '<br>');
}

/**
 * Convert contenteditable HTML back to markdown for sending
 */
export function htmlToMarkdown(html) {
  if (!html || typeof html !== 'string') return '';
  const div = document.createElement('div');
  div.innerHTML = html;

  function process(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return '';

    const tag = node.tagName?.toLowerCase();
    const children = Array.from(node.childNodes)
      .map(process)
      .join('');

    if (tag === 'br') return '\n';
    if (tag === 'pre' && node.querySelector('code')) {
      const code = node.querySelector('code');
      const lang = node.getAttribute('data-lang') || node.dataset?.lang || '';
      return `\n\`\`\`${lang}\n${code.textContent}\n\`\`\`\n`;
    }
    if (tag === 'code' && !node.closest('pre')) {
      return `\`${node.textContent}\``;
    }
    if (tag === 'span' && node.classList?.contains('msg-input-flowdiagram')) {
      const json = node.getAttribute('data-flowdiagram') || '';
      if (json) return `\n\`\`\`flowdiagram\n${json}\n\`\`\`\n`;
      return '';
    }
    if (tag === 'img') {
      const src = node.getAttribute('src') || '';
      const alt = node.getAttribute('alt') || 'Image';
      return `![${alt}](${src})`;
    }
    if (tag === 'a') {
      const href = node.getAttribute('href') || '';
      const text = node.textContent || href;
      return `[${text}](${href})`;
    }
    if (tag === 'div' || tag === 'p') {
      return children + '\n';
    }
    return children;
  }

  return process(div).replace(/\n{3,}/g, '\n\n').trim();
}

/**
 * Get plain text from HTML (for isEmpty check)
 */
export function htmlToText(html) {
  if (!html) return '';
  const div = document.createElement('div');
  div.innerHTML = html;
  return (div.textContent || '').trim();
}
