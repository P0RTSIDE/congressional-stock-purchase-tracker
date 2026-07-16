import type { TooltipProps } from "recharts";

const TOOLTIP_STYLE = {
  background: "#f4f6fb",
  border: "1px solid #c5cdd9",
  borderRadius: 10,
  boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
  padding: "10px 12px",
};

const LABEL_STYLE = { color: "#1a1f2a", fontWeight: 700, marginBottom: 6 };
const ITEM_STYLE = { color: "#2d3548", fontSize: 13 };

export function ChartTooltip({
  active,
  payload,
  label,
  labelFormatter,
}: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;

  const title = labelFormatter ? labelFormatter(label, payload) : label;

  return (
    <div style={TOOLTIP_STYLE}>
      {title && <div style={LABEL_STYLE}>{title}</div>}
      {payload.map((entry, i) => (
        <div key={i} style={{ ...ITEM_STYLE, marginTop: 4 }}>
          <span style={{ color: entry.color ?? "#2d3548", fontWeight: 600 }}>
            {entry.name ?? entry.dataKey}:{" "}
          </span>
          {entry.value}
        </div>
      ))}
    </div>
  );
}
