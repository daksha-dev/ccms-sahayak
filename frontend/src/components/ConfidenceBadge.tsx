export function ConfidenceBadge({ score, conflict }: { score: number; conflict: boolean }) {
  const label = conflict
    ? "CONFLICT"
    : score >= 0.85
    ? "HIGH"
    : score >= 0.55
    ? "MEDIUM"
    : score === 0
    ? "UNREADABLE"
    : "LOW";

  let bg: string, text: string, border: string;
  if (conflict || score < 0.55) {
    bg = "#fff0f0"; text = "#b42318"; border = "#f5c6c2";
  } else if (score >= 0.85) {
    bg = "#fff8ed"; text = "#c46205"; border = "#ffd18a";   // saffron-toned HIGH
  } else {
    bg = "#f0d9b0"; text = "#9e4a08"; border = "#d4a55c";   // warm amber MEDIUM
  }

  return (
    <span
      className="rounded-full border px-2 py-0.5 text-xs font-bold"
      style={{ background: bg, color: text, borderColor: border }}
    >
      {label}
    </span>
  );
}
