export function Methodology() {
  return (
    <div className="page methodology-page">
      <header className="hero">
        <h1>Methodology</h1>
        <p className="hero-sub">
          How this dashboard connects congressional stock trades to votes on
          controversial bills. Everything here is about timing overlap and thematic
          links, not proof of wrongdoing or stock price impact.
        </p>
      </header>

      <section className="panel">
        <h2>What you are looking at</h2>
        <p>
          Members of Congress must disclose stock trades on a public form called a
          Periodic Transaction Report. This dashboard checks whether a member traded
          certain stocks in the year before voting on a bill that could plausibly
          affect those companies or sectors.
        </p>
        <p>
          When we find a match, we flag it as a <strong>timing signal</strong>. That
          means the trade and the vote happened close together in time and the stock
          sits on our exposure list for that bill. It does <strong>not</strong> mean
          the member traded because of the bill, or that their vote moved the stock
          price.
        </p>
      </section>

      <section className="panel">
        <h2>Where the data comes from</h2>
        <ul className="method-list">
          <li>
            <strong>Stock trades:</strong> Public congressional disclosure records,
            including the member&apos;s name, stock ticker, buy or sell, trade date,
            and a dollar range (not an exact amount).
          </li>
          <li>
            <strong>Votes:</strong> Official House and Senate roll-call vote records.
          </li>
          <li>
            <strong>Bills:</strong> A curated set of high-profile legislation, with
            titles and vote dates drawn from Congress.gov.
          </li>
        </ul>
      </section>

      <section className="panel">
        <h2>How we decide which stocks relate to a bill</h2>
        <p>
          Each bill has a hand-picked list of stock tickers that might have thematic
          exposure if the bill passes or fails. These are educated guesses about which
          companies or sectors could be affected, not a verified list of winners and
          losers.
        </p>
        <p>Examples:</p>
        <ul className="method-list">
          <li>Social media and AI bills may include platforms like Meta or Google.</li>
          <li>AI infrastructure bills may include chip and cloud companies.</li>
          <li>Defense and space bills may include major aerospace contractors.</li>
          <li>Energy bills may include oil, gas, and clean-energy names.</li>
        </ul>
        <p>
          Each ticker gets a short explanation and a confidence label: plausible
          direct link, possible indirect link, weak thematic link, or unclear. These
          are editorial judgments, not measured market impact.
        </p>
      </section>

      <section className="panel">
        <h2>How timing signals are counted</h2>
        <ul className="method-list">
          <li>
            We look at trades up to <strong>365 days before</strong> each vote.
          </li>
          <li>
            A signal is created when the same member traded a mapped stock on or
            before the vote date.
          </li>
          <li>
            Trades are grouped as purchases or sales. Trades in the $50,001+
            disclosure bracket are also marked as large.
          </li>
          <li>
            Disclosures are often filed weeks after the actual trade. &quot;Days
            before vote&quot; uses the trade date from the filing, not when it was
            submitted.
          </li>
        </ul>
      </section>

      <section className="panel">
        <h2>Party split</h2>
        <p>
          The same rules apply to Democrats and Republicans. Party breakdowns on the
          dashboard count how many signals each party has, not who did something wrong.
        </p>
      </section>

      <section className="panel">
        <h2>Member pre-vote summaries</h2>
        <p>
          For each flagged member, the dashboard shows what they bought or sold, how
          much (in federal disclosure brackets), how many days before the vote, and
          why that stock might relate to the bill. We also show their recorded
          roll-call position (Yea, Nay, etc.) from public vote records. That position
          is factual only and does not explain why they voted that way or whether the
          trade was related.
        </p>
      </section>

      <section className="panel">
        <h2>What this cannot tell you</h2>
        <ul className="method-list">
          <li>Whether a trade caused a stock to go up or down.</li>
          <li>Whether a member knew about the bill when they traded.</li>
          <li>Exact trade amounts (only wide federal ranges are public).</li>
          <li>Trades held by a spouse, trust, or fund that were not disclosed under the member&apos;s name.</li>
          <li>Every stock that could possibly be affected by a bill.</li>
        </ul>
        <p>
          Over a full year, many ordinary portfolio trades will overlap with a vote by
          chance. Treat every signal as a starting point for questions, not a
          conclusion.
        </p>
      </section>
    </div>
  );
}
