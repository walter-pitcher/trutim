/** Creative SVG background - abstract interconnected nodes (network/chat theme) */
export default function DecorativeSvg({ className = '', variant = 'dashboard' }) {
  const isCompact = variant === 'compact';

  return (
    <svg
      className={className}
      viewBox="0 0 800 600"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      {/* Floating nodes - constellation style */}
      <g opacity={isCompact ? 0.3 : 0.45}>
        {[
          [120, 80, 12],
          [280, 120, 8],
          [450, 60, 14],
          [620, 140, 10],
          [180, 220, 6],
          [350, 280, 11],
          [520, 240, 9],
          [90, 350, 8],
          [250, 400, 12],
          [430, 420, 7],
          [600, 380, 10],
          [710, 320, 9],
        ].map(([x, y, r], i) => (
          <circle key={i} cx={x} cy={y} r={r} fill="var(--accent)" />
        ))}
      </g>
      {/* Connecting lines */}
      <g stroke="var(--accent)" strokeWidth="1" strokeOpacity="0.2">
        <line x1="120" y1="80" x2="280" y2="120" />
        <line x1="280" y1="120" x2="450" y2="60" />
        <line x1="450" y1="60" x2="620" y2="140" />
        <line x1="120" y1="80" x2="180" y2="220" />
        <line x1="280" y1="120" x2="350" y2="280" />
        <line x1="350" y1="280" x2="520" y2="240" />
        <line x1="180" y1="220" x2="90" y2="350" />
        <line x1="350" y1="280" x2="250" y2="400" />
        <line x1="520" y1="240" x2="430" y2="420" />
        <line x1="250" y1="400" x2="430" y2="420" />
        <line x1="430" y1="420" x2="600" y2="380" />
        <line x1="600" y1="380" x2="710" y2="320" />
      </g>
      {/* Decorative rings */}
      <circle cx="400" cy="300" r="180" stroke="var(--accent)" strokeWidth="0.5" fill="none" opacity="0.08" />
      <circle cx="400" cy="300" r="240" stroke="var(--accent)" strokeWidth="0.5" fill="none" opacity="0.05" />
    </svg>
  );
}
