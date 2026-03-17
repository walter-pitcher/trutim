import { useRef, useEffect } from 'react';
import { useChat } from '@ai-sdk/react';
import { TextStreamChatTransport } from 'ai';
import './AIPromptPanel.css';

export default function AIPromptPanel({ onClose, isOpen }) {
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const { messages, sendMessage, status, error, clearError } = useChat({
    transport: new TextStreamChatTransport({
      api: '/api/ai/chat/',
      headers: () => {
        const token = localStorage.getItem('access');
        return token ? { Authorization: `Bearer ${token}` } : {};
      },
      credentials: 'include',
    }),
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen && status === 'ready') {
      inputRef.current?.focus();
    }
  }, [isOpen, status]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const input = inputRef.current;
    if (!input?.value?.trim()) return;
    sendMessage({ text: input.value.trim() });
    input.value = '';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="ai-panel-overlay" onClick={onClose}>
      <div className="ai-prompt-panel" onClick={(e) => e.stopPropagation()}>
        <div className="ai-panel-header">
          <div className="ai-panel-title">
            <span className="ai-panel-icon">✨</span>
            AI Assistant
          </div>
          <button type="button" onClick={onClose} className="ai-panel-close" title="Close">
            ×
          </button>
        </div>

        <div className="ai-panel-messages">
          {messages.length === 0 && (
            <div className="ai-panel-empty">
              <p>Ask me anything. I can help with ideas, writing, or answering questions.</p>
              <p className="ai-panel-hint">Try: &quot;Summarize this for me&quot; or &quot;Help me brainstorm...&quot;</p>
            </div>
          )}
          {messages.map((msg) => {
            const isStreamingLast = status === 'streaming' && msg.role === 'assistant' && msg === messages[messages.length - 1];
            return (
              <div key={msg.id} className={`ai-message ai-message-${msg.role}`}>
                <div className="ai-message-role">
                  {msg.role === 'user' ? 'You' : 'AI'}
                </div>
                <div className={`ai-message-content ${isStreamingLast ? 'ai-streaming' : ''}`}>
                  {msg.parts
                    ?.filter((p) => p.type === 'text')
                    .map((p, i) => (
                      <span key={i}>{p.text}</span>
                    ))}
                  {isStreamingLast && <span className="ai-cursor" />}
                </div>
              </div>
            );
          })}
          {status === 'streaming' && (!messages.length || messages[messages.length - 1]?.role !== 'assistant') && (
            <div className="ai-message ai-message-assistant">
              <div className="ai-message-role">AI</div>
              <div className="ai-message-content ai-streaming">
                <span className="ai-cursor" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="ai-panel-error">
            {error.message}
            <button type="button" onClick={clearError} className="ai-error-dismiss">
              Dismiss
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="ai-panel-form">
          <textarea
            ref={inputRef}
            placeholder="Type your message..."
            rows={1}
            onKeyDown={handleKeyDown}
            disabled={status === 'streaming' || status === 'submitted'}
            className="ai-panel-input"
          />
          <button
            type="submit"
            disabled={status === 'streaming' || status === 'submitted'}
            className="ai-panel-send"
            title="Send"
          >
            {status === 'streaming' || status === 'submitted' ? (
              <span className="ai-send-spinner" />
            ) : (
              'Send'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
