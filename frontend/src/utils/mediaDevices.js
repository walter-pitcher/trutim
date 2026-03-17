/**
 * Media devices utilities - safe access to getUserMedia.
 * Handles missing navigator.mediaDevices (e.g. non-secure context).
 */

export function getMediaDevices() {
  if (typeof navigator === 'undefined') return null;
  return navigator.mediaDevices || null;
}

export function isMediaSupported() {
  const md = getMediaDevices();
  return md && typeof md.getUserMedia === 'function';
}

export function getMediaErrorMessage(err) {
  if (!isMediaSupported()) {
    return 'Camera and microphone require a secure context (HTTPS or localhost). Please use https:// or open from localhost.';
  }
  if (err && err.name === 'NotAllowedError') {
    return 'Permission denied. Please allow camera and microphone access.';
  }
  if (err && err.name === 'NotFoundError') {
    return 'No camera or microphone found.';
  }
  if (err && err.message) {
    return err.message;
  }
  return 'Could not access camera or microphone.';
}

export async function getUserMedia(constraints) {
  const md = getMediaDevices();
  if (!md || !md.getUserMedia) {
    throw new Error(getMediaErrorMessage(null));
  }
  return md.getUserMedia(constraints);
}

export async function getDisplayMedia(constraints) {
  const md = getMediaDevices();
  if (!md || !md.getDisplayMedia) {
    throw new Error('Screen sharing requires a secure context (HTTPS or localhost).');
  }
  return md.getDisplayMedia(constraints);
}
