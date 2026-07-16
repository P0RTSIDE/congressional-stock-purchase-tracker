import { useEffect, useState } from "react";
import type { MemberPreVoteSummary } from "../types";

interface MemberSummariesProps {
  summaries: MemberPreVoteSummary[];
  billTitle?: string | null;
  billSummary?: string | null;
}

function formatDate(iso: string) {
  return new Date(iso + "T12:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const EXPOSURE_CLASS: Record<string, string> = {
  "Strong link": "conf-high",
  "Some connection": "conf-med",
  "Loose connection": "conf-low",
  "Weak connection": "conf-weak",
  "Unclear connection": "conf-weak",
};

export function MemberSummaries({ summaries, billTitle, billSummary }: MemberSummariesProps) {
  const [expandedId, setExpandedId] = useState<string | null>(
    summaries[0]?.member_id ?? null,
  );

  useEffect(() => {
    setExpandedId(summaries[0]?.member_id ?? null);
  }, [billTitle, summaries]);

  if (!summaries.length) {
    return (
      <section className="panel">
        <h2>Member pre-vote summaries</h2>
        <p className="panel-desc">No mapped pre-vote trades for this bill.</p>
      </section>
    );
  }

  return (
    <section className="panel member-summaries">
      <h2>Member pre-vote summaries</h2>
      <p className="panel-desc">
        What each flagged member disclosed before voting on{" "}
        <strong>{billTitle ?? "this bill"}</strong>. Trades are sorted from the
        strongest bill link to the weakest.
      </p>
      {billSummary && (
        <p className="bill-summary-inline">
          <strong>Bill summary:</strong> {billSummary}
        </p>
      )}
      <div className="member-summary-list">
        {summaries.map((member) => {
          const open = expandedId === member.member_id;
          return (
            <article key={member.member_id} className="member-summary-card">
              <button
                type="button"
                className="member-summary-header"
                onClick={() =>
                  setExpandedId(open ? null : member.member_id)
                }
                aria-expanded={open}
              >
                <div className="member-summary-title">
                  <span className="member-summary-name">{member.member_name}</span>
                  <span className={`pill pill-${member.party_at_vote.toLowerCase()}`}>
                    {member.party_at_vote}
                  </span>
                </div>
                <div className="member-summary-meta">
                  <span>{member.trade_count} trades</span>
                  <span>Closest: {member.min_days_before_vote} days before vote</span>
                  {member.vote_position_label &&
                    member.vote_position_label !== "Not available" && (
                      <span>Voted: {member.vote_position_label}</span>
                    )}
                </div>
                <p className="member-summary-overview">{member.overview}</p>
              </button>
              {open && (
                <div className="member-summary-body">
                  {member.trades.map((trade, idx) => (
                    <div key={`${trade.ticker}-${trade.transaction_date}-${idx}`} className="member-trade-row">
                      <div className="member-trade-head">
                        <span className={`pill pill-${trade.transaction_type === "purchase" ? "buy" : "sell"}`}>
                          {trade.transaction_type} {trade.ticker}
                        </span>
                        <span className="member-trade-amount">{trade.amount_label}</span>
                        <span className="member-trade-date">
                          {formatDate(trade.transaction_date)} ({trade.days_before_vote} days before vote)
                        </span>
                      </div>
                      <div className="member-trade-exposure">
                        <span
                          className={`confidence-pill ${
                            EXPOSURE_CLASS[trade.exposure_label] ?? "conf-weak"
                          }`}
                        >
                          {trade.exposure_label}
                        </span>
                      </div>
                      <p className="member-trade-rationale">
                        <strong>How this stock relates to the bill:</strong>{" "}
                        {trade.exposure_plain ?? trade.exposure_rationale}
                      </p>
                      <p className="member-trade-impact">
                        This shows a possible connection, not proof the trade was
                        tied to the vote or that the vote changed the stock price.
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
