import { getStatusIcon } from './icons';

/**
 * Avatar component - displays user avatar image or fallback initial
 * @param {Object} user - User object (may have status: 'active'|'idle'|'deactive')
 * @param {number} size - Avatar size in px
 * @param {boolean} showStatus - Show status badge (default: true when status exists)
 */
export default function Avatar({ user, size = 32, className = '', showStatus = true }) {
  const name = user?.username || user?.first_name || '?';
  const initial = (name.charAt(0) || '?').toUpperCase();
  const src = user?.avatar;
  const status = user?.status || 'deactive';
  const badgeSize = Math.max(10, size * 0.35);

  const style = { width: size, height: size, fontSize: size * 0.4 };

  const avatarEl = src ? (
    <img
      src={src.startsWith('http') ? src : src.startsWith('/') ? src : `/${src}`}
      alt={name}
      className={`avatar avatar-img ${className}`}
      style={style}
    />
  ) : (
    <div className={`avatar avatar-initial ${className}`} style={style} title={name}>
      {initial}
    </div>
  );

  if (showStatus) {
    return (
      <span className="avatar-wrapper">
        {avatarEl}
        <span className="status-badge-wrap">{getStatusIcon(status, { size: badgeSize })}</span>
      </span>
    );
  }

  return avatarEl;
}
