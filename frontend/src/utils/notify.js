/**
 * Browser notification utility - best practice implementation
 * Uses Notification API for desktop notifications when tab is backgrounded
 */

const APP_NAME = 'Trutim';

/**
 * Check if notifications are supported
 */
export function isSupported() {
  return 'Notification' in window;
}

/**
 * Get current permission state
 */
export function getPermission() {
  if (!isSupported()) return 'denied';
  return Notification.permission;
}

/**
 * Request notification permission from the user
 * @returns {Promise<'granted'|'denied'|'default'>}
 */
export async function requestPermission() {
  if (!isSupported()) return 'denied';
  if (Notification.permission === 'granted') return 'granted';
  if (Notification.permission === 'denied') return 'denied';
  return Notification.requestPermission();
}

/**
 * Show a browser notification
 * @param {string} title - Notification title
 * @param {object} options - Notification options
 * @param {string} [options.body] - Notification body text
 * @param {string} [options.icon] - Icon URL
 * @param {string} [options.tag] - Tag to replace existing notifications
 * @param {boolean} [options.requireInteraction] - Stay until user interacts
 * @returns {Notification|null} The notification or null if not shown
 */
export function notify(title, options = {}) {
  if (!isSupported()) return null;
  if (Notification.permission !== 'granted') return null;

  const defaultOptions = {
    body: options.body || '',
    icon: options.icon || '/trutim.png',
    tag: options.tag || 'default',
    requireInteraction: false,
    silent: true,
    ...options,
  };

  try {
    return new Notification(title, defaultOptions);
  } catch (_) {
    return null;
  }
}

/**
 * Show notification for a new chat message
 * Only shows when document is hidden (tab in background) and message is from others
 * @param {string} senderName - Username of sender
 * @param {string} content - Message content preview
 * @param {string} roomName - Room/contact name
 */
export function notifyNewMessage(senderName, content, roomName) {
  if (!document.hidden) return null;
  const body = content?.length > 80 ? `${content.slice(0, 80)}...` : content || 'New message';
  return notify(`${senderName} in ${roomName}`, {
    body,
    tag: `msg-${roomName}-${Date.now()}`,
    requireInteraction: false,
  });
}

export default { isSupported, getPermission, requestPermission, notify, notifyNewMessage };
