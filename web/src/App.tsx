import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartTooltip } from "./components/ChartTooltip";
import { MemberSummaries } from "./components/MemberSummaries";
import { ScatterHoverCard, TradeDetailPanel } from "./components/TradeDetailPanel";
import { Methodology } from "./Methodology";
import { votePositionLabel } from "./voteLabels";
import type { DashboardData, SignalPoint } from "./types";

const PARTY_COLORS: Record<string, string> = {
  D: "#4a9eed",
  R: "#e85d5d",
  I: "#a78bfa",
};

const TYPE_COLORS: Record<string, string> = {
  purchase: "#3ecf8e",
  sale: "#f0a030",
};

function formatDate(iso: string) {
  return new Date(iso + "T12:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hoveredTrade, setHoveredTrade] = useState<SignalPoint | null>(null);
  const [pinnedTrade, setPinnedTrade] = useState<SignalPoint | null>(null);
  const [selectedBillId, setSelectedBillId] = useState<string | null>(null);
  const [page, setPage] = useState<"dashboard" | "methodology">("dashboard");

  useEffect(() => {
    fetch("/data/dashboard.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => {
        setData(d);
        setSelectedBillId(d.primary_bill_id ?? d.bills?.[0]?.bill_id ?? null);
      })
      .catch(() =>
        setError(
          "Dashboard data could not be loaded. Please refresh the page or try again later.",
        ),
      );
  }, []);

  const activeTrade = pinnedTrade ?? hoveredTrade;

  const billSignals = useMemo(() => {
    if (!data) return [];
    const billId = selectedBillId ?? data.primary_bill_id;
    if (!billId) return data.signals;
    return data.signals.filter((s) => s.bill_id === billId);
  }, [data, selectedBillId]);

  const activeBill = useMemo(() => {
    if (!data) return null;
    const billId = selectedBillId ?? data.primary_bill_id;
    return data.bills?.find((b) => b.bill_id === billId) ?? data.bill;
  }, [data, selectedBillId]);

  const timelineData = useMemo(() => {
    if (!billSignals.length) return [];
    const buckets = new Map<number, { days: number; purchase: number; sale: number }>();
    const seen = new Set<string>();
    for (const s of billSignals) {
      const key = `${s.days_before_vote}|${s.transaction_type}|${s.ticker}|${s.transaction_date}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const days = s.days_before_vote;
      const entry = buckets.get(days) ?? { days, purchase: 0, sale: 0 };
      if (s.transaction_type === "purchase") entry.purchase += 1;
      else entry.sale += 1;
      buckets.set(days, entry);
    }
    return Array.from(buckets.values())
      .map((b) => ({ days: b.days, purchase: b.purchase, sale: b.sale }))
      .sort((a, b) => b.days - a.days);
  }, [billSignals]);

  const scatterData = useMemo(() => {
    if (!billSignals.length) return [];
    const seen = new Set<string>();
    return billSignals
      .filter((s) => {
        const key = `${s.member_name}|${s.ticker}|${s.transaction_date}|${s.transaction_type}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((s) => ({
        ...s,
        x: s.days_before_vote,
        y: s.ticker,
        large: (s.amount_max ?? 0) >= 50001,
      }));
  }, [billSignals]);

  const byMember = useMemo(() => {
    const map = new Map<string, {
      member_name: string;
      member_id: string;
      party_at_vote: string;
      vote_position_label?: string;
      signals: number;
      purchases: number;
      sales: number;
      large_trades: number;
      tickers: Set<string>;
      min_days: number;
    }>();
    for (const s of billSignals) {
      const key = s.member_id ?? s.member_name;
      const row = map.get(key) ?? {
        member_name: s.member_name,
        member_id: s.member_id ?? key,
        party_at_vote: s.party_at_vote,
        vote_position_label: votePositionLabel(s.vote_position, s.vote_position_label),
        signals: 0,
        purchases: 0,
        sales: 0,
        large_trades: 0,
        tickers: new Set<string>(),
        min_days: s.days_before_vote,
      };
      row.signals += 1;
      if (s.transaction_type === "purchase") row.purchases += 1;
      if (s.transaction_type === "sale") row.sales += 1;
      if ((s.amount_max ?? 0) >= 50001) row.large_trades += 1;
      row.tickers.add(s.ticker);
      row.min_days = Math.min(row.min_days, s.days_before_vote);
      map.set(key, row);
    }
    return Array.from(map.values())
      .map((r) => ({ ...r, tickers: Array.from(r.tickers) }))
      .sort((a, b) => b.signals - a.signals);
  }, [billSignals]);

  const byTicker = useMemo(() => {
    const map = new Map<string, { ticker: string; signals: number; purchases: number; sales: number; members: Set<string> }>();
    for (const s of billSignals) {
      const row = map.get(s.ticker) ?? { ticker: s.ticker, signals: 0, purchases: 0, sales: 0, members: new Set() };
      row.signals += 1;
      if (s.transaction_type === "purchase") row.purchases += 1;
      if (s.transaction_type === "sale") row.sales += 1;
      if (s.member_id) row.members.add(s.member_id);
      map.set(s.ticker, row);
    }
    return Array.from(map.values())
      .map((r) => ({ ...r, members: r.members.size }))
      .sort((a, b) => b.signals - a.signals);
  }, [billSignals]);

  const signalTypes = useMemo(() => {
    const labels: Record<string, string> = {
      purchase_before_vote: "Purchases",
      sale_before_vote: "Sales",
      large_purchase: "Large buys",
      large_sale: "Large sells",
    };
    const colors: Record<string, string> = {
      purchase_before_vote: "#3ecf8e",
      sale_before_vote: "#f0a030",
      large_purchase: "#c77dff",
      large_sale: "#e85d5d",
    };
    const counts: Record<string, number> = {};
    for (const s of billSignals) {
      counts[s.signal_type] = (counts[s.signal_type] ?? 0) + 1;
    }
    return Object.entries(counts).map(([k, v]) => ({
      name: labels[k] ?? k,
      value: v,
      fill: colors[k] ?? "#8b93a7",
    }));
  }, [billSignals]);

  const memberSummaries = useMemo(() => {
    if (!data) return [];
    const billId = selectedBillId ?? data.primary_bill_id;
    if (!billId || !data.member_summaries_by_bill) return [];
    return data.member_summaries_by_bill[billId] ?? [];
  }, [data, selectedBillId]);

  if (error) {
    return (
      <div className="error">
        <p>{error}</p>
      </div>
    );
  }

  if (!data) {
    return <div className="loading">Loading congressional timing data…</div>;
  }

  const { summary, bill, ticker_context } = data;
  const billTitle = (activeBill as { title?: string })?.title ?? bill.title;
  const billSummary = (activeBill as { summary?: string })?.summary ?? bill.summary;
  const billVoteDate = (activeBill as { vote_date?: string })?.vote_date ?? bill.vote_date;
  const billTags = (activeBill as { tags?: string[] })?.tags ?? bill.tags;

  const partyCounts = { D: 0, R: 0 };
  for (const s of billSignals) {
    if (s.party_at_vote === "D") partyCounts.D += 1;
    if (s.party_at_vote === "R") partyCounts.R += 1;
  }
  const partyTotal = partyCounts.D + partyCounts.R || 1;
  const demPct = Math.round((100 * partyCounts.D) / partyTotal);
  const repPct = 100 - demPct;

  const billSignalCount = billSignals.length;
  const billMemberCount = new Set(billSignals.map((s) => s.member_id)).size;
  const billLargeCount = billSignals.filter((s) => (s.amount_max ?? 0) >= 50001).length;

  if (page === "methodology") {
    return (
      <>
        <nav className="site-nav">
          <button type="button" className="nav-link" onClick={() => setPage("dashboard")}>
            Dashboard
          </button>
          <button type="button" className="nav-link nav-link-active">
            Methodology
          </button>
        </nav>
        <Methodology />
      </>
    );
  }

  return (
    <>
      <nav className="site-nav">
        <button type="button" className="nav-link nav-link-active">
          Dashboard
        </button>
        <button type="button" className="nav-link" onClick={() => setPage("methodology")}>
          Methodology
        </button>
      </nav>
    <div className="page">
      <header className="hero">
        <h1>Congressional stock trades before controversial votes</h1>
        <p className="hero-sub">
          Select a bill below to see when members traded mapped tickers before
          voting. Timing overlap only, not proof of wrongdoing or insider trading.
        </p>
      </header>

      <div className="disclaimer">{data.framing}</div>

      <section className="exposure-explainer">
        <h2>Does this vote affect the stocks?</h2>
        <p>{data.exposure_framing}</p>
        {billTags && (
          <div className="tag-row">
            {billTags.map((t) => (
              <span key={t} className="tag">
                {t.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        )}
        <ul className="exposure-legend">
          <li>
            <span className="confidence-pill conf-high">Plausible direct</span> AI platforms
            (META, GOOG) on TikTok/KOSA/deepfake bills; chip/cloud on environmental AI bills
          </li>
          <li>
            <span className="confidence-pill conf-med">Possible indirect</span> Suppliers or
            adjacent tech (e.g. NVDA, AMZN/Kuiper)
          </li>
          <li>
            <span className="confidence-pill conf-low">Weak thematic</span> Broad sector map
            (e.g. CVX, JPM), included for completeness, not strong linkage
          </li>
        </ul>
      </section>

      {data.bills && data.bills.length > 0 && (
        <div className="bill-tabs" role="tablist" aria-label="Select legislation">
          <span className="bill-tabs-label">Select legislation</span>
          {data.bills.map((b) => (
            <button
              key={b.bill_id}
              type="button"
              className={`bill-tab ${selectedBillId === b.bill_id ? "bill-tab-active" : ""}`}
              role="tab"
              aria-selected={selectedBillId === b.bill_id}
              onClick={() => {
                setSelectedBillId(b.bill_id);
                setPinnedTrade(null);
                setHoveredTrade(null);
              }}
            >
              <span className="bill-tab-title">{b.title ?? b.bill_id}</span>
              <span className="bill-tab-meta">{b.signal_count} signals</span>
            </button>
          ))}
        </div>
      )}

      <div className="vote-marker">
        <span>
          Focus bill: <strong>{billTitle ?? selectedBillId}</strong>
        </span>
        <span>·</span>
        <span>Vote: {billVoteDate ? formatDate(billVoteDate) : "unknown"}</span>
        <span>·</span>
        <span>365-day lookback window</span>
      </div>

      {billSummary && (
        <section className="bill-summary panel">
          <h2>What this bill does</h2>
          <p>{billSummary}</p>
        </section>
      )}

      <div className="stats">
        <div className="stat">
          <div className="stat-value">{billSignalCount}</div>
          <div className="stat-label">Timing signals</div>
        </div>
        <div className="stat">
          <div className="stat-value">{billMemberCount}</div>
          <div className="stat-label">Members flagged</div>
        </div>
        <div className="stat">
          <div className="stat-value">{billLargeCount}</div>
          <div className="stat-label">Large trades ($50k+)</div>
        </div>
        <div className="stat">
          <div className="stat-value">{byTicker.length}</div>
          <div className="stat-label">Tickers matched</div>
        </div>
      </div>

      <div className="grid-2">
        <section className="panel">
          <h2>Trades clustering before the vote</h2>
          <p className="panel-desc">
            Each bar = disclosed trades in a bucket before the roll call.
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={timelineData.filter((_, i) => i % 3 === 0).slice(0, 40)}
              margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="days" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                content={<ChartTooltip />}
                labelFormatter={(d) => `${d} days before vote`}
              />
              <Legend />
              <Bar dataKey="purchase" name="Purchases" stackId="a" fill="#3ecf8e" />
              <Bar dataKey="sale" name="Sales" stackId="a" fill="#f0a030" radius={[4, 4, 0, 0]} />
              <ReferenceLine x={30} stroke="#f5c542" strokeDasharray="4 4" label="30 days" />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="panel">
          <h2>Signal breakdown</h2>
          <p className="panel-desc">Purchases vs. sales, including large-trade flags.</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={signalTypes} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                {signalTypes.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="panel scatter-section">
        <h2>Who traded what, and how close to the vote?</h2>
        <p className="panel-desc">
          Hover for a quick summary · <strong>click a dot to pin</strong> the full context panel.
          Green = buy, orange = sell, larger dot = $50k+ bracket.
        </p>
        <div className="scatter-layout">
          <div className="scatter-chart-wrap">
            <ResponsiveContainer width="100%" height={480}>
              <ScatterChart margin={{ top: 12, right: 20, bottom: 20, left: 12 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="x"
                  domain={[0, 365]}
                  reversed
                  label={{ value: "Days before vote →", position: "insideBottom", offset: -8 }}
                  tick={{ fontSize: 10 }}
                />
                <YAxis
                  type="category"
                  dataKey="y"
                  width={48}
                  tick={{ fontSize: 10 }}
                  interval={0}
                />
                <Tooltip
                  content={
                    <ScatterHoverCard tickerContext={ticker_context} />
                  }
                  cursor={{ strokeDasharray: "3 3", stroke: "#8b93a7" }}
                  wrapperStyle={{ zIndex: 20, pointerEvents: "none" }}
                />
                <Scatter
                  data={scatterData}
                  shape="circle"
                  className="scatter-dots"
                  onClick={(d) => setPinnedTrade(d as SignalPoint)}
                  onMouseEnter={(d) => {
                    if (!pinnedTrade) setHoveredTrade(d as SignalPoint);
                  }}
                  onMouseLeave={() => {
                    if (!pinnedTrade) setHoveredTrade(null);
                  }}
                >
                  {scatterData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={TYPE_COLORS[entry.transaction_type] ?? "#8b93a7"}
                      opacity={
                        activeTrade &&
                        activeTrade.member_name === entry.member_name &&
                        activeTrade.ticker === entry.ticker &&
                        activeTrade.transaction_date === entry.transaction_date
                          ? 1
                          : entry.large
                            ? 0.85
                            : 0.55
                      }
                      stroke={
                        activeTrade &&
                        activeTrade.member_name === entry.member_name &&
                        activeTrade.ticker === entry.ticker &&
                        activeTrade.transaction_date === entry.transaction_date
                          ? "#f5c542"
                          : "transparent"
                      }
                      strokeWidth={2}
                      r={entry.large ? 8 : 5}
                      style={{ cursor: "pointer" }}
                    />
                  ))}
                </Scatter>
                <ReferenceLine x={90} stroke="#f5c542" strokeDasharray="4 4" />
                <ReferenceLine x={30} stroke="#e85d5d" strokeDasharray="4 4" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <TradeDetailPanel
            trade={activeTrade}
            tickerContext={
              activeTrade ? ticker_context?.[activeTrade.ticker] : undefined
            }
            billTitle={billTitle}
            billSummary={billSummary}
            exposureNote={bill.exposure_note}
            pinned={!!pinnedTrade}
            onClose={() => setPinnedTrade(null)}
          />
        </div>
      </section>

      <div className="grid-2">
        <section className="panel">
          <h2>Party split (symmetric methodology)</h2>
          <p className="panel-desc">Same detection logic applied to D and R voters.</p>
          <div className="party-bar">
            <div
              className="party-seg"
              style={{ width: `${demPct}%`, background: PARTY_COLORS.D }}
            >
              {demPct > 12 && `D ${demPct}%`}
            </div>
            <div
              className="party-seg"
              style={{ width: `${repPct}%`, background: PARTY_COLORS.R }}
            >
              {repPct > 12 && `R ${repPct}%`}
            </div>
          </div>
          <div className="party-legend">
            <span>
              <span className="legend-dot" style={{ background: PARTY_COLORS.D }} />
              Democrats: {partyCounts.D} signals
            </span>
            <span>
              <span className="legend-dot" style={{ background: PARTY_COLORS.R }} />
              Republicans: {partyCounts.R} signals
            </span>
          </div>
        </section>

        <section className="panel">
          <h2>Most-traded exposed tickers</h2>
          <p className="panel-desc">Hover bars for counts. Link strength varies by ticker.</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={byTicker.slice(0, 8)} margin={{ left: 0, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="ticker" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="signals" name="Signals" fill="#4a9eed" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="panel">
        <h2>Members with the most pre-vote activity</h2>
        <p className="panel-desc">
          Sorted by timing signals. &quot;How they voted&quot; is their recorded choice on
          this bill&apos;s roll-call vote (Yea, Nay, etc.) from public House or Senate records.
          &quot;Closest&quot; = fewest days between trade and vote.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Member</th>
                <th>Party</th>
                <th>How they voted</th>
                <th>Signals</th>
                <th>Buys</th>
                <th>Sells</th>
                <th>Large</th>
                <th>Closest trade</th>
                <th>Tickers</th>
              </tr>
            </thead>
            <tbody>
              {byMember.slice(0, 15).map((m) => (
                <tr key={m.member_id}>
                  <td>{m.member_name}</td>
                  <td>
                    <span className={`pill pill-${m.party_at_vote.toLowerCase()}`}>
                      {m.party_at_vote}
                    </span>
                  </td>
                  <td>{m.vote_position_label ?? "Not available"}</td>
                  <td>{m.signals}</td>
                  <td>
                    <span className="pill pill-buy">{m.purchases}</span>
                  </td>
                  <td>
                    <span className="pill pill-sell">{m.sales}</span>
                  </td>
                  <td>{m.large_trades}</td>
                  <td>{m.min_days} days before</td>
                  <td>{m.tickers.slice(0, 5).join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <MemberSummaries
        summaries={memberSummaries}
        billTitle={billTitle}
        billSummary={billSummary}
      />

      <footer className="footer">
        Data from public congressional disclosure and vote records. Last updated{" "}
        {new Date(data.generated_at).toLocaleString()}. See{" "}
        <button type="button" className="footer-link" onClick={() => setPage("methodology")}>
          Methodology
        </button>{" "}
        for how this dashboard works.
      </footer>
    </div>
    </>
  );
}
