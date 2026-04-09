import Link from "next/link";
import { useRouter } from "next/router";
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

export default function BotProfilePage() {
  const router = useRouter();
  const { id } = router.query;
  const [bot, setBot] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    if (!id) {
      return;
    }
    setError("");
    try {
      setBot(await apiGet(`/bots/public/${id}`));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  if (error) {
    return <p className="error">{error}</p>;
  }

  if (!bot) {
    return <p className="muted">Loading bot profile...</p>;
  }

  return (
    <div className="stack">
      <section className="hero stack">
        <p className="muted">{bot.strategy_type}</p>
        <h1>{bot.display_name}</h1>
        <p>{bot.persona}</p>
        <div className="grid two">
          <article className="panel stack">
            <strong>Portfolio value</strong>
            <span>{formatCurrency(bot.portfolio_value)} Terracoin</span>
            <span className="muted">Wallet: {formatCurrency(bot.wallet_balance)}</span>
          </article>
          <article className="panel stack">
            <strong>Track record</strong>
            <span>Unrealized P/L: {formatCurrency(bot.total_unrealized_pl)}</span>
            <span>Realized P/L: {formatCurrency(bot.realized_pl)}</span>
            <span>Avg confidence: {formatPercent(bot.avg_confidence)}</span>
          </article>
          <article className="panel stack">
            <strong>Research mode</strong>
            <span>{bot.commentary_mode || "standard commentary"}</span>
            <span>{bot.search_enabled ? "Curated web search enabled" : "Stored data only"}</span>
          </article>
          <article className="panel stack">
            <strong>Source usage</strong>
            <span>Research runs: {bot.research_runs}</span>
            <span>Stored citations: {bot.stored_citation_count}</span>
            <span>External citations: {bot.external_citation_count}</span>
          </article>
        </div>
      </section>

      <section className="panel stack">
        <h2>Open positions</h2>
        {bot.open_positions.length === 0 ? <p className="muted">No open positions yet.</p> : null}
        {bot.open_positions.map((position) => (
          <article className="market-card" key={`${position.market_id}:${position.outcome}`}>
            <strong>{position.market_title}</strong>
            <span>
              {position.outcome} · {position.shares.toFixed(2)} shares
            </span>
            <span>Cost basis: {formatCurrency(position.cost_basis)}</span>
            <span>Current value: {formatCurrency(position.current_value)}</span>
            <span>Unrealized P/L: {formatCurrency(position.unrealized_pl)}</span>
            <Link className="btn secondary" href={`/markets/${position.market_slug}`}>
              Open market
            </Link>
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Settled positions</h2>
        {bot.settled_positions.length === 0 ? <p className="muted">No settled positions yet.</p> : null}
        {bot.settled_positions.map((position) => (
          <article className="market-card" key={`${position.market_id}:${position.outcome}`}>
            <strong>{position.market_title}</strong>
            <span>
              {position.outcome} · {position.shares.toFixed(2)} shares
            </span>
            <span>Cost basis: {formatCurrency(position.cost_basis)}</span>
            <span>Realized P/L: {formatCurrency(position.realized_pl)}</span>
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Recent theses and trades</h2>
        {bot.recent_runs.length === 0 ? <p className="muted">No bot runs yet.</p> : null}
        {bot.recent_runs.map((run) => (
          <article className="market-card" key={run.id}>
            <strong>{run.market_title || run.market_slug || "Unknown market"}</strong>
            <span>
              {run.action_type}
              {run.outcome ? ` ${run.outcome}` : ""} · Confidence {formatPercent(run.confidence)}
            </span>
            {run.shares ? <span>Shares: {run.shares.toFixed(2)}</span> : null}
            {run.thesis_summary ? <p className="muted">{run.thesis_summary}</p> : null}
            <CitationList citations={run.citations || []} title="Sources" />
            {run.market_slug ? (
              <Link className="btn secondary" href={`/markets/${run.market_slug}`}>
                Open market
              </Link>
            ) : null}
            <span className="muted">{new Date(run.finished_at || run.started_at).toLocaleString()}</span>
          </article>
        ))}
      </section>
    </div>
  );
}
