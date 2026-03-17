function getSentimentLabel(score) {
  if (score <= -60) return { text: 'Very Bearish', color: 'text-loss' };
  if (score <= -20) return { text: 'Bearish', color: 'text-loss-muted' };
  if (score <= 20) return { text: 'Neutral', color: 'text-text-muted' };
  if (score <= 60) return { text: 'Bullish', color: 'text-gain-muted' };
  return { text: 'Very Bullish', color: 'text-gain' };
}

export default function SentimentBar({ score = 0 }) {
  const clampedScore = Math.max(-100, Math.min(100, score));
  const fillWidth = ((clampedScore + 100) / 200) * 100;
  const { text, color } = getSentimentLabel(clampedScore);

  return (
    <div>
      {/* Bar */}
      <div className="bg-bg-elevated rounded-full h-2 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${fillWidth}%`,
            background: `linear-gradient(to right, #EF4444, #F59E0B, #22C55E)`,
            backgroundSize: '200% 100%',
            backgroundPosition: `${100 - fillWidth}% 0`,
          }}
        />
      </div>

      {/* Labels */}
      <div className="flex items-center justify-between mt-1.5">
        <span className={`text-sm font-medium ${color}`}>{text}</span>
        <span className={`font-mono text-sm ${color}`}>
          {clampedScore > 0 ? '+' : ''}{clampedScore}
        </span>
      </div>
    </div>
  );
}
