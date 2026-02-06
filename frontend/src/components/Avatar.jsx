/**
 * Avatar component - displays user avatar image or fallback initial
 */
export default function Avatar({ user, size = 32, className = '' }) {
  const name = user?.username || user?.first_name || '?';
  const initial = (name.charAt(0) || '?').toUpperCase();
  const src = user?.avatar;

  const style = { width: size, height: size, fontSize: size * 0.4 };

  if (src) {
    const imgSrc = src.startsWith('http') ? src : src.startsWith('/') ? src : `/${src}`;
    return (
      <img
        src={imgSrc}
        alt={name}
        className={`avatar avatar-img ${className}`}
        style={style}
      />
    );
  }

  return (
    <div
      className={`avatar avatar-initial ${className}`}
      style={style}
      title={name}
    >
      {initial}
    </div>
  );
}
