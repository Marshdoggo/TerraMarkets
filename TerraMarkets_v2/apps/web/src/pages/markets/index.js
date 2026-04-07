import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
export { emptyServerProps as getServerSideProps } from "../../lib/ssr";

function sortOdds(prices = {}) {
  return Object.entries(prices).sort((left, right) => right[1] - left[1]);
}

export default function MarketsPage() {
  const [markets, setMarkets] = useState([]);
  const [error, setError] = useState("");
  const [view, setView] = useState("open");
  const filteredMarkets = markets.filter((market) => {
    if (view === "resolved") {
      return market.status === "resolved";
    }
    return market.status === "open";
  });

  useEffect(() => {
    apiGet("/markets").then(setMarkets).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="stack">
      <section className="hero stack">
        <h1>Markets</h1>
        <p className="muted">Open science forecasting markets priced by LMSR.</p>
        <div className="actions">
          <button
            className={view === "open" ? "btn primary" : "btn"}
            type="button"
            onClick={() => setView("open")}
          >
            Open
          </button>
          <button
            className={view === "resolved" ? "btn primary" : "btn"}
            type="button"
            onClick={() => setView("resolved")}
          >
            Resolved
          </button>
        </div>
      </section>
      {error ? <p className="error">{error}</p> : null}
      <section className="grid two">
        {filteredMarkets.map((market) => (
          <article className="market-card market-card-featured" key={market.id}>
            <div className="market-odds-strip">
              {sortOdds(market.prices).map(([label, value]) => (
                <div className="odds-chip" key={label}>
                  <span className="odds-chip-label">{label}</span>
                  <strong>{(value * 100).toFixed(1)}%</strong>
                </div>
              ))}
            </div>
            <div className="stack">
              <strong>{market.title}</strong>
              <span className="market-meta">{market.slug}</span>
              <span>Category: {market.category}</span>
              <span className="muted">{market.description || "No description provided."}</span>
            </div>
            <div className="stack">
              <span>Status: {market.status}</span>
              <span>Closes: {new Date(market.close_at).toLocaleString()}</span>
              {sortOdds(market.prices)[0] ? (
                <span className="market-leading-odds">
                  Leading view: {sortOdds(market.prices)[0][0]} at {(sortOdds(market.prices)[0][1] * 100).toFixed(1)}%
                </span>
              ) : null}
              <span>Outcomes: {market.outcomes.join(", ")}</span>
              {market.resolved_outcome ? <span>Resolved: {market.resolved_outcome}</span> : null}
            </div>
            <Link className="btn primary" href={`/markets/${market.slug}`}>
              View market
            </Link>
          </article>
        ))}
        {filteredMarkets.length === 0 && !error ? (
          <p className="muted">{view === "open" ? "No open markets right now." : "No resolved markets yet."}</p>
        ) : null}
      </section>
    </div>
  );
}
