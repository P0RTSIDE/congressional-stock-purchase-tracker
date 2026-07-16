import type { SignalPoint, TickerContext } from "../types";
import { votePositionLabel } from "../voteLabels";

const AFFECTS_LABELS: Record<string, { label: string; className: string }> = {
  plausible_direct: { label: "Plausible direct link", className: "conf-high" },
  possible_indirect: { label: "Possible indirect link", className: "conf-med" },
  weak_thematic: { label: "Weak thematic link", className: "conf-low" },
  unlikely_direct: { label: "Unlikely direct link", className: "conf-weak" },
  unclear: { label: "Unclear link", className: "conf-weak" },
};

function formatDate(iso: string) {
  return new Date(iso + "T12:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatAmount(min: number | null | undefined, max: number | null | undefined) {
  const hi = max ?? min;
  if (!hi) return "Amount not disclosed";
  if (hi >= 50001) return "$50,001 to $100,000+";
  if (hi >= 15001) return "$15,001 to $50,000";
  return "$1,001 to $15,000";
}

function votePillClass(position?: string) {
  switch ((position ?? "").toLowerCase()) {
    case "yea":
      return "pill-vote-yea";
    case "nay":
      return "pill-vote-nay";
    default:
      return "pill-vote-other";
  }
}

interface TradeDetailPanelProps {
  trade: SignalPoint | null;
  tickerContext?: TickerContext;
  billTitle?: string | null;
  billSummary?: string | null;
  exposureNote?: string;
  onClose?: () => void;
  pinned?: boolean;
}

export function TradeDetailPanel({
  trade,
  tickerContext,
  billTitle,
  billSummary,
  exposureNote,
  onClose,
  pinned = false,
}: TradeDetailPanelProps) {
  if (!trade) {
    return (
      <aside className="detail-panel detail-panel-empty">
        <h3>Trade context</h3>
        <p>
          Hover or <strong>click a dot</strong> on the scatter chart to see whether
          this bill plausibly affects that ticker, and what the member disclosed.
        </p>
      </aside>
    );
  }

  const affects = tickerContext
    ? AFFECTS_LABELS[tickerContext.affects_stock] ?? AFFECTS_LABELS.unclear
    : AFFECTS_LABELS.unclear;
  const confidencePct = tickerContext
    ? Math.round((tickerContext.confidence ?? 0) * 100)
    : null;

  return (
    <aside className={`detail-panel ${pinned ? "detail-panel-pinned" : ""}`}>
      <div className="detail-panel-header">
        <h3>{trade.member_name}</h3>
        {pinned && onClose && (
          <button type="button" className="detail-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        )}
      </div>

      <div className="detail-grid">
        <div className="detail-row">
          <span className="detail-label">Trade</span>
          <span className={`pill pill-${trade.transaction_type === "purchase" ? "buy" : "sell"}`}>
            {trade.transaction_type} {trade.ticker}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Disclosed</span>
          <span>{formatDate(trade.transaction_date)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Amount</span>
          <span>{formatAmount(trade.amount_min, trade.amount_max)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Roll call</span>
          <span>
            {billTitle ?? trade.bill_title} · {formatDate(trade.vote_date)}
          </span>
        </div>
        {votePositionLabel(trade.vote_position, trade.vote_position_label) && (
          <div className="detail-row">
            <span className="detail-label">How they voted</span>
            <span className={`pill ${votePillClass(trade.vote_position)}`}>
              {votePositionLabel(trade.vote_position, trade.vote_position_label)}
            </span>
          </div>
        )}
        <div className="detail-row">
          <span className="detail-label">Timing</span>
          <span>
            <strong>{trade.days_before_vote} days</strong> before roll call
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Party</span>
          <span className={`pill pill-${trade.party_at_vote.toLowerCase()}`}>
            {trade.party_at_vote}
          </span>
        </div>
      </div>

      {billSummary && (
        <div className="detail-section detail-bill-summary">
          <h4>What this bill does</h4>
          <p className="detail-rationale">{billSummary}</p>
        </div>
      )}

      <div className="detail-section">
        <h4>Does this vote affect {trade.ticker}?</h4>
        <span className={`confidence-pill ${affects.className}`}>{affects.label}</span>
        {confidencePct !== null && (
          <span className="confidence-score">Exposure confidence: {confidencePct}%</span>
        )}
        <p className="detail-rationale">
          {tickerContext?.rationale ??
            "This ticker was on the bill's curated exposure list. Specific market impact is not verified."}
        </p>
        <p className="detail-caveat">
          <strong>Important:</strong> A timing overlap is not proof the member traded because
          of this bill, or that the vote moved the stock price. The roll-call position shown
          is from public records and does not explain why the member voted that way.
        </p>
      </div>

      {exposureNote && <p className="detail-footnote">{exposureNote}</p>}
      {!pinned && (
        <p className="detail-hint">Click the dot to pin this panel</p>
      )}
    </aside>
  );
}

interface ScatterTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: SignalPoint & { x: number; y: string; large: boolean } }>;
  tickerContext?: Record<string, TickerContext>;
}

export function ScatterHoverCard({ active, payload, tickerContext }: ScatterTooltipProps) {
  if (!active || !payload?.[0]) return null;
  const p = payload[0].payload;
  const ctx = tickerContext?.[p.ticker];
  const affects = ctx
    ? AFFECTS_LABELS[ctx.affects_stock]?.label ?? "Unclear link"
    : "Mapped ticker";

  return (
    <div className="scatter-tooltip">
      <div className="scatter-tooltip-title">
        {p.member_name} · {p.transaction_type.toUpperCase()} {p.ticker}
      </div>
      <div className="scatter-tooltip-row">
        <span>Trade date</span>
        <span>{formatDate(p.transaction_date)}</span>
      </div>
      <div className="scatter-tooltip-row">
        <span>How they voted</span>
        <span>
          {votePositionLabel(p.vote_position, p.vote_position_label) ?? "Not available"}
        </span>
      </div>
      <div className="scatter-tooltip-row">
        <span>Days before vote</span>
        <span>{p.days_before_vote}</span>
      </div>
      <div className="scatter-tooltip-row">
        <span>Bill link</span>
        <span>{affects}</span>
      </div>
      <div className="scatter-tooltip-hint">Click to pin full context</div>
    </div>
  );
}
