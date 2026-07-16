export interface TickerContext {
  ticker: string;
  confidence: number;
  rationale: string;
  link_type: string;
  affects_stock: string;
}

export interface SignalPoint {
  member_name: string;
  member_id?: string;
  bill_id?: string;
  bill_title?: string;
  party_at_vote: string;
  ticker: string;
  transaction_type: string;
  transaction_date: string;
  vote_date: string;
  days_before_vote: number;
  amount_min?: number | null;
  amount_max: number | null;
  signal_type: string;
  vote_position?: string;
  vote_position_label?: string;
}

export interface MemberTradeSummary {
  ticker: string;
  transaction_type: string;
  transaction_date: string;
  amount_label: string;
  days_before_vote: number;
  exposure_label: string;
  exposure_confidence: number;
  exposure_rationale: string;
  exposure_plain?: string;
}

export interface MemberPreVoteSummary {
  member_id: string;
  member_name: string;
  party_at_vote: string;
  vote_position?: string;
  vote_position_label?: string;
  trade_count: number;
  purchases: number;
  sales: number;
  large_trades: number;
  min_days_before_vote: number;
  overview: string;
  trades: MemberTradeSummary[];
  trade_details: string[];
}

export interface DashboardData {
  generated_at: string;
  framing: string;
  exposure_framing?: string;
  summary: {
    total_signals: number;
    unique_members: number;
    unique_bills: number;
    by_signal_type: Record<string, number>;
    by_party: Record<string, number>;
    large_trades: number;
    cross_party: { count: number; pct: number };
    non_cross_party: { count: number; pct: number };
  };
  bill: {
    bill_id: string | null;
    title: string | null;
    summary?: string | null;
    vote_date: string | null;
    tags?: string[];
    sector?: string;
    salience?: number;
    exposure_note?: string;
  };
  bills?: Array<{
    bill_id: string;
    title: string | null;
    summary?: string | null;
    vote_date: string | null;
    tags?: string[];
    sector?: string;
    signal_count: number;
    member_count: number;
    ticker_count: number;
  }>;
  primary_bill_id?: string | null;
  focus_topic?: string;
  focus_tags?: string[];
  ticker_context?: Record<string, TickerContext>;
  member_summaries_by_bill?: Record<string, MemberPreVoteSummary[]>;
  by_member: Array<{
    member_name: string;
    member_id: string;
    party_at_vote: string;
    signals: number;
    purchases: number;
    sales: number;
    large_trades: number;
    tickers: string[];
    min_days: number;
  }>;
  by_ticker: Array<{
    ticker: string;
    signals: number;
    purchases: number;
    sales: number;
    members: number;
  }>;
  timeline: Array<{
    days_before_vote: number;
    transaction_type: string;
    count: number;
  }>;
  signals: SignalPoint[];
}
