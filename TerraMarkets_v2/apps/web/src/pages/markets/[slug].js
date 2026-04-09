import { useRouter } from "next/router";
import Link from "next/link";
import { useEffect, useState } from "react";
import CitationList from "../../components/CitationList";
import OddsPieChart from "../../components/OddsPieChart";
import TimeSeriesChart from "../../components/TimeSeriesChart";
import { apiGet, apiPost } from "../../lib/api";
export { emptyServerProps as getServerSideProps } from "../../lib/ssr";

function formatDelta(value, unit) {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(3)} ${unit || ""}`.trim();
}

function sortOdds(prices = {}) {
  return Object.entries(prices).sort((left, right) => right[1] - left[1]);
}

export default function MarketDetailPage() {
  const router = useRouter();
  const { slug } = router.query;
  const [market, setMarket] = useState(null);
  const [commentary, setCommentary] = useState([]);
  const [me, setMe] = useState(null);
  const [shares, setShares] = useState("10");
  const [outcome, setOutcome] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function load() {
    if (!slug) {
      return;
    }
    try {
      const marketData = await apiGet(`/markets/${slug}`);
      setMarket(marketData);
      setOutcome((current) => current || marketData.outcomes[0] || "");
      try {
        const commentaryData = await apiGet(`/markets/${slug}/bot-commentary`);
        setCommentary(commentaryData);
      } catch {
        setCommentary([]);
      }
      try {
        const meData = await apiGet("/auth/me");
        setMe(meData);
      } catch {
        setMe(null);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [slug]);

  async function handleBuy(event) {
    event.preventDefault();
    setError("");
    setStatus("");
    try {
      const result = await apiPost(`/markets/${slug}/buy`, {
        outcome,
        shares: Number(shares),
      });
      setStatus(`Bought shares. Cost: ${result.cost.toFixed(2)} at average price ${result.avg_price.toFixed(4)}.`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleResolve(selectedOutcome) {
    const confirmed = window.confirm(`Resolve this market as ${selectedOutcome}? This will settle the market.`);
    if (!confirmed) {
      return;
    }
    setError("");
    setStatus("");
    try {
      const result = await apiPost(`/markets/${slug}/resolve`, { outcome: selectedOutcome });
      setStatus(`Resolved ${selectedOutcome}. Total paid: ${result.total_paid.toFixed(2)}.`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) {
    return <p className="error">{error}</p>;
  }

  if (!market) {
    return <p className="muted">Loading market...</p>;
  }

  const botOutcomeCounts = commentary.reduce((counts, item) => {
    if (item.outcome) {
      counts[item.outcome] = (counts[item.outcome] || 0) + 1;
    }
    return counts;
  }, {});
  const activeBotVotes = Object.values(botOutcomeCounts).reduce((total, count) => total + count, 0);
  const botLeader = Object.entries(botOutcomeCounts).sort((left, right) => right[1] - left[1])[0] || null;

  return (
    <div className="grid two">
      <section className="panel stack">
        <h1>{market.title}</h1>
        <p className="muted">{market.slug}</p>
        <p>Category: {market.category}</p>
        <p>{market.description || "No description provided."}</p>
        <p>Status: {market.status}</p>
        <p>Closes: {new Date(market.close_at).toLocaleString()}</p>
        <p>Resolution criteria: {market.resolution_criteria}</p>
        {market.resolved_outcome ? <p>Resolved outcome: {market.resolved_outcome}</p> : null}
        <div className="market-odds-panel">
          <div className="stack">
            <strong>Current odds</strong>
            <div className="market-odds-grid">
              {sortOdds(market.prices).map(([label, value]) => (
                <article className="odds-stat-card" key={label}>
                  <span className="market-meta">{label}</span>
                  <strong className="odds-stat-value">{(value * 100).toFixed(1)}%</strong>
                </article>
              ))}
            </div>
            {sortOdds(market.prices)[0] ? (
              <span className="muted">
                Market-implied leader: {sortOdds(market.prices)[0][0]} at {(sortOdds(market.prices)[0][1] * 100).toFixed(1)}%
              </span>
            ) : null}
          </div>
          <OddsPieChart prices={market.prices} />
        </div>
        <div className="stack">
          <h3>Odds history</h3>
          {market.snapshots?.length ? (
            market.snapshots.slice(0, 8).map((snapshot) => (
              <article className="market-card" key={snapshot.id}>
                <strong>{snapshot.event_type}</strong>
                <span className="muted">{snapshot.created_at}</span>
                <span>Total LMSR cost: {snapshot.total_cost.toFixed(4)}</span>
                {Object.entries(snapshot.prices).map(([label, value]) => (
                  <span key={label}>
                    {label}: {(value * 100).toFixed(2)}%
                  </span>
                ))}
              </article>
            ))
          ) : (
            <p className="muted">No snapshots yet.</p>
          )}
        </div>
        <div className="stack">
          <h3>Data links</h3>
          {market.data_links?.length ? (
            market.data_links.map((link) => {
              const recentPoints = link.recent_points || [];
              const latestPoint = recentPoints[recentPoints.length - 1] || null;
              const oneWeekAgoPoint = recentPoints.length >= 8 ? recentPoints[recentPoints.length - 8] : null;
              const weekDelta =
                latestPoint &&
                oneWeekAgoPoint &&
                latestPoint.numeric_value !== null &&
                oneWeekAgoPoint.numeric_value !== null
                  ? latestPoint.numeric_value - oneWeekAgoPoint.numeric_value
                  : null;
              const recentTrend =
                weekDelta === null
                  ? "n/a"
                  : weekDelta > 0
                    ? "rising over the last week"
                    : weekDelta < 0
                      ? "falling over the last week"
                      : "flat over the last week";

              return (
                <article className="market-card" key={link.id}>
                  <strong>{link.label}</strong>
                  <span>
                    {link.source_key}:{link.series_key}
                  </span>
                  {link.latest_numeric_value !== null ? (
                    <span>
                      Latest observation: {link.latest_numeric_value} {link.latest_unit || ""}
                    </span>
                  ) : (
                    <span className="muted">No stored observation yet.</span>
                  )}
                  {link.latest_observed_at ? <span className="muted">Observed at {link.latest_observed_at}</span> : null}
                  {recentPoints.length ? (
                    <div className="grid two">
                      <div className="panel stack">
                        <strong>Latest value</strong>
                        <span>
                          {latestPoint?.numeric_value !== null ? `${latestPoint.numeric_value.toFixed(3)} ${link.latest_unit || ""}` : "n/a"}
                        </span>
                      </div>
                      <div className="panel stack">
                        <strong>1 week delta</strong>
                        <span>{weekDelta !== null ? formatDelta(weekDelta, link.latest_unit) : "n/a"}</span>
                        <span className="muted">{recentTrend}</span>
                      </div>
                    </div>
                  ) : null}
                  {recentPoints.length ? (
                    <TimeSeriesChart
                      points={recentPoints}
                      ariaLabel={`${link.label} recent history`}
                      unit={link.latest_unit}
                    />
                  ) : null}
                  {link.notes ? <span className="muted">{link.notes}</span> : null}
                </article>
              );
            })
          ) : (
            <p className="muted">No linked science data yet.</p>
          )}
        </div>
      </section>

      <section className="panel stack">
        <h2>Buy shares</h2>
        {status ? <p className="notice">{status}</p> : null}
        <form className="stack" onSubmit={handleBuy}>
          <label className="field">
            <span>Outcome</span>
            <select value={outcome} onChange={(event) => setOutcome(event.target.value)}>
              {market.outcomes.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Shares</span>
            <input type="number" min="0.01" step="0.01" value={shares} onChange={(event) => setShares(event.target.value)} />
          </label>
          <button className="btn primary" type="submit">
            Buy
          </button>
        </form>

        {me?.tier === "admin" && market.status === "open" ? (
          <div className="stack">
            <h3>Resolve market</h3>
            <div className="actions">
              {market.outcomes.map((label) => (
                <button className="btn danger" key={label} onClick={() => handleResolve(label)} type="button">
                  Resolve as {label}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="stack">
          <h2>Bot activity</h2>
          <div className="grid two">
            <article className="market-card">
              <strong>Bot lean</strong>
              <span>{botLeader ? `${botLeader[0]} (${botLeader[1]} thesis-backed signal${botLeader[1] === 1 ? "" : "s"})` : "No lean yet"}</span>
              <span className="muted">{activeBotVotes} recent bot theses with explicit outcomes.</span>
            </article>
            <article className="market-card">
              <strong>Disagreement</strong>
              {Object.keys(botOutcomeCounts).length ? (
                Object.entries(botOutcomeCounts).map(([label, count]) => (
                  <span key={label}>
                    {label}: {count}
                  </span>
                ))
              ) : (
                <span className="muted">Run bots to compare bullish and bearish theses.</span>
              )}
            </article>
          </div>
          <h2>Bot theses</h2>
          {commentary.length === 0 ? (
            <p className="muted">No bot theses yet. Run a bot cycle to generate commentary for this market.</p>
          ) : null}
          {commentary.map((item) => (
            <article className="market-card" key={item.id}>
              <strong>
                <Link href={`/bots/${item.bot_profile_id}`}>{item.bot_display_name}</Link>
              </strong>
              <span className="muted">{item.strategy_type}</span>
              <span>{item.bot_persona}</span>
              <span>
                {item.action_type}
                {item.outcome ? ` ${item.outcome}` : ""}
                {item.confidence !== null ? ` · confidence ${(item.confidence * 100).toFixed(0)}%` : ""}
              </span>
              {item.shares ? <span>Shares: {item.shares.toFixed(2)}</span> : null}
              {item.thesis_summary ? <p className="muted">{item.thesis_summary}</p> : null}
              <CitationList citations={item.citations || []} title="Sources" />
              <span className="muted">{new Date(item.created_at).toLocaleString()}</span>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
