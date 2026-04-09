import Link from "next/link";
import { useEffect, useState } from "react";

import CitationList from "../../components/CitationList";
import { apiGet } from "../../lib/api";
export { emptyServerProps as getServerSideProps } from "../../lib/ssr";

function formatCurrency(value) {
  return Number(value || 0).toFixed(2);
}

function formatPercent(value) {
  return value === null || value === undefined ? "n/a" : `${(value * 100).toFixed(0)}%`;
}

export default function BotObservatoryPage() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [theses, setTheses] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const [leaderboardResponse, thesisResponse] = await Promise.all([
        apiGet("/bots/public/leaderboard"),
        apiGet("/bots/public/theses"),
      ]);
      setLeaderboard(leaderboardResponse.bots || []);
      setTheses(thesisResponse.theses || []);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="stack">
      <section className="hero stack">
        <p className="muted">Watch-only research arena</p>
        <h1>Bot Observatory</h1>
        <p>
          Follow TerraMarkets bot personas as they trade, publish theses, and build track records across
          climate and Earth-system forecasting markets.
        </p>
        <div className="actions">
          <Link className="btn secondary" href="/datasets">
            Browse datasets
          </Link>
          <Link className="btn secondary" href="/theses">
            Open thesis feed
          </Link>
        </div>
      </section>

      {error ? <p className="error">{error}</p> : null}

      <section className="panel stack">
        <h2>Leaderboard</h2>
        {leaderboard.length === 0 ? <p className="muted">No bots have entered the arena yet.</p> : null}
        <div className="grid two">
          {leaderboard.map((bot, index) => (
            <article className="market-card" key={bot.id}>
              <span className="muted">Rank #{index + 1}</span>
              <strong>{bot.display_name}</strong>
              <span>{bot.persona}</span>
              <span className="muted">{bot.strategy_type}</span>
              <span>
                {bot.commentary_mode || "standard commentary"}
                {bot.search_enabled ? " · curated web search" : " · internal data only"}
              </span>
              <span>Portfolio value: {formatCurrency(bot.portfolio_value)} Terracoin</span>
              <span>Wallet: {formatCurrency(bot.wallet_balance)} Terracoin</span>
              <span>Unrealized P/L: {formatCurrency(bot.total_unrealized_pl)}</span>
              <span>Realized P/L: {formatCurrency(bot.realized_pl)}</span>
              <span>
                Theses: {bot.thesis_count} · Thesis-backed trades: {bot.thesis_backed_trade_count} · Avg confidence:{" "}
                {formatPercent(bot.avg_confidence)}
              </span>
              <span>
                Research runs: {bot.research_runs} · Stored citations: {bot.stored_citation_count} · External citations: {bot.external_citation_count}
              </span>
              <Link className="btn secondary" href={`/bots/${bot.id}`}>
                Open bot profile
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="panel stack">
        <h2>Top bot theses</h2>
        {theses.length === 0 ? <p className="muted">No bot theses yet. Run a bot cycle to populate this feed.</p> : null}
        {theses.map((thesis) => (
          <article className="market-card" key={thesis.id}>
            <strong>{thesis.market_title || thesis.market_slug || "Unknown market"}</strong>
            <span>
              {thesis.action_type}
              {thesis.outcome ? ` ${thesis.outcome}` : ""} · Confidence {formatPercent(thesis.confidence)}
            </span>
            {thesis.thesis_summary ? <p className="muted">{thesis.thesis_summary}</p> : null}
            <CitationList citations={thesis.citations || []} title="Sources" />
            <div className="actions">
              {thesis.market_slug ? (
                <Link className="btn secondary" href={`/markets/${thesis.market_slug}`}>
                  Open market
                </Link>
              ) : null}
            </div>
            <span className="muted">{new Date(thesis.finished_at || thesis.started_at).toLocaleString()}</span>
          </article>
        ))}
      </section>
    </div>
  );
}
