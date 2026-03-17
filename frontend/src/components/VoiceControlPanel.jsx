import { useState } from 'react';
import { MicIcon, XIcon } from './icons';
import './VoiceControlPanel.css';

export default function VoiceControlPanel({
  isOpen,
  onClose,
  connected,
  listening,
  detectorState,
  lastCommandResult,
  startListening,
  stopListening,
  sendTextCommand,
}) {
  const [textCommand, setTextCommand] = useState('');

  if (!isOpen) return null;

  const handleSendCommand = () => {
    const trimmed = textCommand.trim();
    if (trimmed && sendTextCommand) {
      sendTextCommand(trimmed);
      setTextCommand('');
    }
  };

  return (
    <div className="voice-control-overlay" onClick={onClose}>
      <div className="voice-control-panel" onClick={(e) => e.stopPropagation()}>
        <div className="voice-control-header">
          <div className="voice-control-title">
            <MicIcon size={20} />
            <span>Voice Control</span>
          </div>
          <button type="button" onClick={onClose} className="voice-control-close" title="Close">
            <XIcon size={18} />
          </button>
        </div>

        <div className="voice-control-body">
          <div className="voice-control-status">
            <span className={`voice-status-dot ${connected ? 'connected' : 'disconnected'}`} />
            <span className="voice-status-text">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {!connected && (
            <p className="voice-control-hint">
              Voice control requires an active connection. Make sure you are in a chat room and logged in.
            </p>
          )}

          {connected && (
            <>
              <div className="voice-control-actions">
                <button
                  type="button"
                  onClick={listening ? stopListening : startListening}
                  disabled={!connected}
                  className={`voice-listen-btn ${listening ? 'active' : ''}`}
                >
                  <MicIcon size={20} />
                  {listening ? 'Stop Listening' : 'Start Listening'}
                </button>
              </div>

              {listening && (
                <div className="voice-listening-indicator">
                  <span className="voice-pulse" />
                  Listening for commands...
                </div>
              )}

              {detectorState && detectorState !== 'IDLE' && (
                <div className="voice-detector-state">State: {detectorState}</div>
              )}

              <div className="voice-control-manual">
                <label className="voice-control-label">Or type a command</label>
                <div className="voice-control-input-row">
                  <input
                    type="text"
                    value={textCommand}
                    onChange={(e) => setTextCommand(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendCommand()}
                    placeholder="e.g. send hello"
                    className="voice-control-input"
                    disabled={!connected}
                  />
                  <button
                    type="button"
                    onClick={handleSendCommand}
                    disabled={!textCommand.trim() || !connected}
                    className="voice-control-send"
                  >
                    Send
                  </button>
                </div>
              </div>

              {lastCommandResult && (
                <div className="voice-last-result">
                  <span className="voice-result-label">Last result:</span>
                  <pre className="voice-result-content">
                    {typeof lastCommandResult === 'object'
                      ? JSON.stringify(lastCommandResult, null, 2)
                      : String(lastCommandResult)}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
