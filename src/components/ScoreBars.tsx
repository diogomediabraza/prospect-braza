interface ScoreBarProps {
  label: string;
  value?: number;
  max?: number;
  color?: string;
}

export function ScoreBar({
  label,
  value = 0,
  max = 10,
  color,
}: ScoreBarProps) {
  const pct = Math.min(100, (value / max) * 100);
  const getColor = () => {
    if (color) return color;
    if (pct >= 70) return "#10b981";
    if (pct >= 40) return "#f59e0b";
    return "#f87171";
  };

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs w-28 flex-shrink-0" style={{ color: "var(--ts)" }}>
        {label}
      </span>
      <div className="score-bar flex-1">
        <div
          className="score-fill"
          style={{ width: `${pct}%`, background: getColor() }}
        />
      </div>
      <span
        className="text-xs font-mono w-8 text-right flex-shrink-0"
        style={{ color: "var(--text)" }}
      >
        {value?.toFixed(1) ?? "—"}
      </span>
    </div>
  );
}

interface ScoreCircleProps {
  value?: number;
  size?: "sm" | "md" | "lg";
}

export function ScoreCircle({ value = 0, size = "md" }: ScoreCircleProps) {
  const pct = Math.min(100, (value / 10) * 100);
  const getColor = () => {
    if (pct >= 70) return "#10b981";
    if (pct >= 40) return "#f59e0b";
    return "#FF5500";
  };

  const sizes = {
    sm: { w: 36, stroke: 3, text: "text-xs" },
    md: { w: 52, stroke: 4, text: "text-sm" },
    lg: { w: 72, stroke: 5, text: "text-base" },
  };
  const s = sizes[size];
  const r = (s.w - s.stroke * 2) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;

  return (
    <div className="relative flex items-center justify-center" style={{ width: s.w, height: s.w }}>
      <svg width={s.w} height={s.w} className="-rotate-90">
        <circle
          cx={s.w / 2}
          cy={s.w / 2}
          r={r}
          stroke="var(--bg3)"
          strokeWidth={s.stroke}
          fill="none"
        />
        <circle
          cx={s.w / 2}
          cy={s.w / 2}
          r={r}
          stroke={getColor()}
          strokeWidth={s.stroke}
          fill="none"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
      </svg>
      <span
        className={`absolute font-mono font-medium ${s.text}`}
        style={{ color: "var(--text)" }}
      >
        {value?.toFixed(0) ?? "—"}
      </span>
    </div>
  );
}
