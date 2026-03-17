/**
 * Resume upload component - PDF or Word documents.
 */
import { useState, useRef } from 'react';
import { FileIcon } from './icons';
import './ResumeUpload.css';

const ACCEPTED_TYPES = 'application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const MAX_SIZE_MB = 5;

export default function ResumeUpload({ user, onUpload, disabled = false }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    const allowed = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ];
    if (!allowed.includes(file.type)) {
      return 'Please select a PDF or Word document (.pdf, .doc, .docx).';
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File must be under ${MAX_SIZE_MB}MB.`;
    }
    return null;
  };

  const handleFile = async (file) => {
    const err = validateFile(file);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      await onUpload(file);
    } catch (e) {
      const msg = e.response?.data?.resume?.[0] ?? e.response?.data?.detail ?? 'Upload failed.';
      setError(typeof msg === 'string' ? msg : 'Upload failed.');
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled || isLoading) return;
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled && !isLoading) setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleClick = () => {
    if (disabled || isLoading) return;
    fileInputRef.current?.click();
  };

  const resumeUrl = user?.resume;
  const hasResume = !!resumeUrl;

  return (
    <div className="resume-upload">
      <div
        className={`resume-upload-area ${isDragging ? 'dragging' : ''} ${isLoading ? 'loading' : ''} ${disabled ? 'disabled' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          onChange={handleChange}
          disabled={disabled || isLoading}
          className="resume-upload-input"
          aria-label="Upload resume"
        />
        <div className="resume-upload-content">
          {isLoading ? (
            <div className="resume-upload-spinner" />
          ) : (
            <>
              <FileIcon size={32} />
              <span className="resume-upload-text">
                {hasResume ? 'Replace resume' : 'Upload resume'}
              </span>
              {hasResume && (
                <a
                  href={resumeUrl.startsWith('http') || resumeUrl.startsWith('/') ? resumeUrl : `/${resumeUrl}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="resume-upload-link"
                  onClick={(e) => e.stopPropagation()}
                >
                  View current
                </a>
              )}
            </>
          )}
        </div>
      </div>
      {error && <p className="resume-upload-error">{error}</p>}
      <p className="resume-upload-hint">PDF or Word. Max {MAX_SIZE_MB}MB.</p>
    </div>
  );
}
