interface RiskScoreBarProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showBar?: boolean;
}

export function getRiskColor(score: number): string {
  if (score >= 90) return "hsl(0, 72%, 51%)";
  if (score >= 70) return "hsl(25, 95%, 53%)";
  if (score >= 50) return "hsl(32, 95%, 44%)";
  return "hsl(160, 84%, 29%)";
}

export function getRiskLabel(score: number): string {
  if (score >= 90) return "CRITICAL";
  if (score >= 70) return "HIGH";
  if (score >= 50) return "MEDIUM";
  return "LOW";
}

export default function RiskScoreBar({ score, size = "sm", showBar = true }: RiskScoreBarProps) {
  const color = getRiskColor(score);
  const fontSize = size === "lg" ? 24 : size === "md" ? 16 : 13;
  const barH = size === "lg" ? 6 : size === "md" ? 4 : 3;

  return (
    <div className="flex flex-col gap-0.5">
      <span style={{ color, fontSize, fontWeight: 700 }}>{score}</span>
      {showBar && (
        <div className="w-full rounded-full overflow-hidden" style={{ height: barH, background: "hsl(var(--border))" }}>
          <div className="h-full rounded-full" style={{ width: `${score}%`, background: color }} />
        </div>
      )}
    </div>
  );
}
