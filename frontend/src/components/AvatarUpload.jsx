/**
 * Professional avatar upload component with drag-and-drop, preview, and loading states.
 */
import { useState, useRef } from 'react';
import { CameraIcon } from './icons';
import './AvatarUpload.css';

const ACCEPTED_TYPES = 'image/jpeg,image/png,image/gif,image/webp';
const MAX_SIZE_MB = 2;

export default function AvatarUpload({ user, onUpload, disabled = false }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    if (!file?.type?.startsWith('image/')) {
      return 'Please select an image file (JPEG, PNG, GIF, or WebP).';
    }
    if (!ACCEPTED_TYPES.split(',').includes(file.type)) {
      return 'Invalid format. Use JPEG, PNG, GIF, or WebP.';
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `Image must be under ${MAX_SIZE_MB}MB.`;
    }
    return null;
  };

  const handleFile = async (file) => {
    const err = validateFile(file);
    if (err) {
      setError(err);
      setPreview(null);
      return;
    }
    setError(null);
    setPreview(URL.createObjectURL(file));
    setIsLoading(true);
    try {
      await onUpload(file);
    } catch (e) {
      const msg = e.response?.data?.avatar?.[0] ?? e.response?.data?.detail ?? 'Upload failed.';
      setError(typeof msg === 'string' ? msg : 'Upload failed.');
    } finally {
      setIsLoading(false);
      setPreview(null);
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

  const displaySrc = preview || user?.avatar;
  const name = user?.username || user?.first_name || '?';
  const initial = (name.charAt(0) || '?').toUpperCase();
  const size = 120;

  return (
    <div className="avatar-upload">
      <div
        className={`avatar-upload-area ${isDragging ? 'dragging' : ''} ${isLoading ? 'loading' : ''} ${disabled ? 'disabled' : ''}`}
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
          className="avatar-upload-input"
          aria-label="Upload avatar"
        />
        <div className="avatar-upload-preview" style={{ width: size, height: size }}>
          {displaySrc ? (
            <img
              src={displaySrc.startsWith('http') || displaySrc.startsWith('/') ? displaySrc : `/${displaySrc}`}
              alt={name}
            />
          ) : (
            <span className="avatar-upload-initial">{initial}</span>
          )}
        </div>
        <div className="avatar-upload-overlay">
          {isLoading ? (
            <div className="avatar-upload-spinner" />
          ) : (
            <>
              <CameraIcon size={24} />
              <span>{isDragging ? 'Drop image here' : 'Change photo'}</span>
            </>
          )}
        </div>
      </div>
      {error && <p className="avatar-upload-error">{error}</p>}
      <p className="avatar-upload-hint">JPEG, PNG, GIF or WebP. Max {MAX_SIZE_MB}MB.</p>
    </div>
  );
}
