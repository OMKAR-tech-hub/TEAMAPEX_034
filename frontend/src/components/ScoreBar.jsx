export default function ScoreBar({ label, score, weight }) {
  const pct = Math.round(score || 0);
  const color = pct >= 75 ? '#1a7c3a' : pct >= 55 ? '#f59e0b' : '#c62828';
  return (
    <div className="score-bar">
      <div className="score-bar-header">
        <span>{label} {weight && <span style={{ color: '#999', fontSize: '0.78rem' }}>({Math.round(weight * 100)}% weight)</span>}</span>
        <strong style={{ color }}>{pct}/100</strong>
      </div>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}
