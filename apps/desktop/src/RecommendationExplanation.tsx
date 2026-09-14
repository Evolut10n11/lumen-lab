import { ChevronRight, Sparkles } from "lucide-react";

type Props = {
  label: string;
  reasons?: string[];
  exclude?: string;
  compact?: boolean;
};

export default function RecommendationExplanation({
  label,
  reasons,
  exclude,
  compact = false,
}: Props) {
  const excluded = exclude?.trim();
  const visible = (reasons ?? [])
    .map((reason) => reason.trim())
    .filter((reason) => reason.length > 0 && reason !== excluded)
    .filter((reason, index, items) => items.indexOf(reason) === index);

  if (visible.length === 0) return null;

  return (
    <details
      className="detail-card"
      data-recommendation-explanation="true"
      style={compact ? { marginTop: 18, padding: 16 } : undefined}
    >
      <summary
        className="text-button"
        style={{
          width: "100%",
          cursor: "pointer",
          listStyle: "none",
          justifyContent: "space-between",
          padding: 0,
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
          <Sparkles size={14} />
          {label}
        </span>
        <ChevronRight size={14} />
      </summary>
      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
        {visible.map((reason) => (
          <p key={reason} style={{ margin: 0 }}>{reason}</p>
        ))}
      </div>
    </details>
  );
}
