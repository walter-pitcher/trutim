import { getStatusIcon } from './icons';

/** Distinct colors for name-based avatar backgrounds */
const AVATAR_COLORS = [
  '#5B8DEE', '#EF6B6B', '#51CF66', '#F59E0B', '#A855F7',
  '#06B6D4', '#EC4899', '#84CC16', '#F97316', '#6366F1',
];

/**
 * Get a consistent color from a name string
 */
function getColorFromName(name) {
  if (!name || name === '?') return AVATAR_COLORS[0];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % AVATAR_COLORS.length;
  return AVATAR_COLORS[index];
}

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
    <div
      className={`avatar avatar-initial ${className}`}
      style={{ ...style, background: getColorFromName(name) }}
      title={name}
    >
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
