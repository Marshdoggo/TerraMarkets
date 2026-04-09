import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

const INGEST_CONTROLS = [
  {
    key: "nsidc_charctic_daily",
    label: "Arctic sea ice",
    description: "Fetches the rolling 365-day NSIDC Arctic window and appends only new observations.",
    fetchPath: "/data/fetch/nsidc-charctic",
    fetchBody: { days: 365 },
  },
  {
    key: "enso_oni",
    label: "ENSO / ONI",
    description: "Fetches the latest NOAA CPC ENSO table and appends only unseen monthly observations.",
    fetchPath: "/data/fetch/enso-oni",
    fetchBody: { source_key: "enso_oni" },
  },
  {
    key: "nsidc_antarctic_daily",
    label: "Antarctic sea ice",
    description: "Fetches the rolling 365-day NSIDC Antarctic window and appends only new observations.",
    fetchPath: "/data/fetch/nsidc-antarctic",
    fetchBody: { days: 365 },
  },
  {
    key: "usgs_earthquakes",
    label: "USGS earthquakes",
    description: "Fetches the USGS monthly GeoJSON feed and appends only unseen events.",
    fetchPath: "/data/fetch/usgs-earthquakes",
    fetchBody: { source_key: "usgs_earthquakes" },
  },
  {
    key: "nasa_donki_solar_flares",
    label: "NASA DONKI solar flares",
    description: "Fetches the DONKI solar flare feed and appends only unseen flare events.",
    fetchPath: "/data/fetch/donki-solar-flares",
    fetchBody: { source_key: "nasa_donki_solar_flares" },
  },
  {
    key: "smithsonian_volcanoes",
    label: "Smithsonian volcanoes",
    description: "Fetches the weekly Smithsonian volcanic activity report and appends eruption/activity counts.",
    fetchPath: "/data/fetch/smithsonian-volcanoes",
    fetchBody: { source_key: "smithsonian_volcanoes" },
    backfillPath: "/data/fetch/smithsonian-volcanoes/backfill",
    backfillBody: { source_key: "smithsonian_volcanoes", weeks: 26, prune_invalid_existing: true },
  },
];

const LINK_DEFAULTS_BY_CATEGORY = {
  "arctic systems": {
    source_key: "nsidc_charctic_daily",
    series_key: "daily_extent_million_sq_km",
    label: "NSIDC Arctic sea ice extent",
    notes: "Daily Arctic sea ice extent from NSIDC Charctic.",
  },
  "enso outlook": {
    source_key: "enso_oni",
    series_key: "oni_index",
    label: "Oceanic Nino Index",
    notes: "NOAA CPC ONI monthly series. Use roni_index if the market is about Relative ONI.",
  },
  earthquakes: {
    source_key: "usgs_earthquakes",
    series_key: "earthquake_magnitude",
    label: "Earthquake magnitude",
    notes: "USGS rolling monthly earthquake magnitudes.",
  },
  "antarctic systems": {
    source_key: "nsidc_antarctic_daily",
    series_key: "daily_extent_million_sq_km",
    label: "NSIDC Antarctic sea ice extent",
    notes: "Daily Antarctic sea ice extent from NSIDC Sea Ice Today.",
  },
  "solar flares": {
    source_key: "nasa_donki_solar_flares",
    series_key: "solar_flare_intensity",
    label: "Solar flare intensity",
    notes: "NASA DONKI flare intensity observations.",
  },
  "volcano activity": {
    source_key: "smithsonian_volcanoes",
    series_key: "weekly_eruption_count",
    label: "Weekly eruption count",
    notes: "Weekly volcanic activity counts derived from the Smithsonian report.",
  },
};

const MARKET_TEMPLATES = [
  {
    key: "antarctic-threshold",
    label: "Antarctic threshold",
    category: "antarctic systems",
    market: {
      slug: "antarctic-sea-ice-threshold",
      title: "Will Antarctic sea ice extent exceed a chosen threshold before close?",
      description: "Template for Antarctic threshold markets linked to NSIDC daily extent.",
      resolution_criteria: "Resolve YES if the linked NSIDC Antarctic daily extent series crosses the stated threshold before this market closes.",
      outcomes: "YES,NO",
      b: "58",
    },
  },
  {
    key: "volcano-count",
    label: "Volcano count",
    category: "volcano activity",
    market: {
      slug: "volcano-weekly-count-template",
      title: "Will the next Smithsonian weekly report exceed a count threshold?",
      description: "Template for eruption-count or active-volcano-count markets.",
      resolution_criteria: "Resolve YES if the linked Smithsonian weekly count is above the stated threshold in the next qualifying report before market close.",
      outcomes: "YES,NO",
      b: "50",
    },
  },
  {
    key: "kp-preview",
    label: "Geomagnetic preview",
    category: "space weather",
    market: {
      slug: "kp-threshold-template",
      title: "Will the daily planetary Kp index exceed a storm threshold?",
      description: "Forward template for future NOAA SWPC Kp markets.",
      resolution_criteria: "Resolve YES if the linked Kp series exceeds the stated threshold before market close.",
      outcomes: "YES,NO",
      b: "52",
    },
  },
];

function getDefaultLinkDraft(category, title = "Reference series") {
  const normalized = (category || "").trim().toLowerCase();
  const base = LINK_DEFAULTS_BY_CATEGORY[normalized] || {
    source_key: "enso_oni",
    series_key: "oni_index",
    label: title,
    notes: "Pick the source and series that match the market resolution criteria.",
  };
  return {
    ...base,
    label: base.label || title,
  };
}

export default function AdminPage() {
  const [markets, setMarkets] = useState([]);
  const [purchaseRequests, setPurchaseRequests] = useState([]);
  const [fetchRequests, setFetchRequests] = useState([]);
  const [users, setUsers] = useState([]);
  const [bots, setBots] = useState([]);
  const [scheduler, setScheduler] = useState({ running: false, poll_interval_seconds: 15, last_tick_at: null });
  const [linkDrafts, setLinkDrafts] = useState({});
  const [botRunMarketSlug, setBotRunMarketSlug] = useState("");
  const [demoSeedSummary, setDemoSeedSummary] = useState(null);
  const [fetchAllResults, setFetchAllResults] = useState([]);
  const [market, setMarket] = useState({
    slug: "",
    title: "",
    category: "climate indicators",
    description: "",
    resolution_criteria: "",
    close_at: "",
    outcomes: "YES,NO",
    b: "50",
  });
  const [mint, setMint] = useState({
    user_id: "",
    amount: "100",
    memo: "Admin mint",
  });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [resolveSelections, setResolveSelections] = useState({});

  function applyTemplate(template) {
    setMarket((current) => ({
      ...current,
      ...template.market,
      category: template.category,
    }));
  }

  async function loadMarkets() {
    try {
      const response = await apiGet("/markets");
      setMarkets(response);
      setResolveSelections((current) => {
        const next = { ...current };
        response.forEach((item) => {
          if (!next[item.slug]) {
            next[item.slug] = item.outcomes[0] || "";
          }
        });
        return next;
      });
      setLinkDrafts((current) => {
        const next = { ...current };
        response.forEach((item) => {
          if (!next[item.slug]) {
            next[item.slug] = getDefaultLinkDraft(item.category, `${item.title} reference series`);
          }
        });
        return next;
      });
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadPurchaseRequests() {
    try {
      const response = await apiGet("/wallet/purchase-requests");
      setPurchaseRequests(response);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadUsers() {
    try {
      const response = await apiGet("/wallet/admin/users");
      setUsers(response);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadFetchRequests() {
    try {
      const response = await apiGet("/data/fetch-requests");
      setFetchRequests(response);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadBots() {
    try {
      const response = await apiGet("/bots");
      setBots(response);
      setBotRunMarketSlug((current) => current || response[0]?.recent_runs?.[0]?.market_slug || "");
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadScheduler() {
    try {
      const response = await apiGet("/bots/scheduler/status");
      setScheduler(response);
    } catch (err) {
      setError(err.message);
    }
  }

  async function refreshAdminData() {
    await Promise.all([
      loadMarkets(),
      loadPurchaseRequests(),
      loadUsers(),
      loadFetchRequests(),
      loadBots(),
      loadScheduler(),
    ]);
  }

  useEffect(() => {
    refreshAdminData();
  }, []);

  async function handleCreateMarket(event) {
    event.preventDefault();
    setError("");
    setStatus("");
    try {
      const payload = {
        slug: market.slug,
        title: market.title,
        category: market.category,
        description: market.description,
        resolution_criteria: market.resolution_criteria,
        close_at: market.close_at,
        outcomes: market.outcomes.split(",").map((value) => value.trim()).filter(Boolean),
        b: Number(market.b),
      };
      await apiPost("/markets", payload);
      setStatus("Market created.");
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleMint(event) {
    event.preventDefault();
    setError("");
    setStatus("");
    try {
      await apiPost("/wallet/mint", {
        user_id: Number(mint.user_id),
        amount: Number(mint.amount),
        memo: mint.memo,
      });
      setStatus("Wallet funded.");
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleResolveMarket(slug) {
    const selectedOutcome = resolveSelections[slug];
    const confirmed = window.confirm(`Resolve ${slug} as ${selectedOutcome}? This will settle the market.`);
    if (!confirmed) {
      return;
    }

    setError("");
    setStatus("");
    try {
      const result = await apiPost(`/markets/${slug}/resolve`, { outcome: selectedOutcome });
      setStatus(`Resolved ${slug} as ${selectedOutcome}. Total paid: ${result.total_paid.toFixed(2)} Terracoin.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleApprovePurchaseRequest(requestId) {
    setError("");
    setStatus("");
    try {
      const result = await apiPost(`/wallet/purchase-requests/${requestId}/approve`, {});
      setStatus(`Approved purchase request #${result.id} for ${result.amount.toFixed(2)} Terracoin.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateLink(slug) {
    const draft = linkDrafts[slug];
    setError("");
    setStatus("");
    try {
      await apiPost(`/markets/${slug}/links`, draft);
      setStatus(`Linked ${slug} to ${draft.source_key}:${draft.series_key}.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleFetchPipeline(control) {
    setError("");
    setStatus("");
    try {
      const run = await apiPost(control.fetchPath, control.fetchBody);
      const inserted = run?.points?.length ?? 0;
      setStatus(`Fetched ${control.label}. ${inserted} new observations were appended.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleFetchAllPipelines() {
    setError("");
    setStatus("");
    setFetchAllResults([]);
    try {
      const response = await apiPost("/data/fetch/all", {});
      setFetchAllResults(response.results || []);
      const succeeded = (response.results || []).filter((result) => result.status === "success").length;
      const failed = (response.results || []).filter((result) => result.status !== "success").length;
      setStatus(`Fetched all datasets. ${succeeded} succeeded, ${failed} failed.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleBackfillVolcanoHistory(control) {
    setError("");
    setStatus("");
    try {
      const run = await apiPost(control.backfillPath, control.backfillBody);
      const inserted = run?.points?.length ?? 0;
      setStatus(`Backfilled ${control.label} history. ${inserted} observations were included in the backfill run.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSeedDemoMarkets() {
    setError("");
    setStatus("");
    try {
      const summary = await apiPost("/markets/seed/demo", {});
      setDemoSeedSummary(summary);
      setStatus(
        `Seeded demo catalog: ${summary.created_markets} new markets, ${summary.existing_markets} existing, ${summary.created_links} new links.`
      );
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSeedBots() {
    setError("");
    setStatus("");
    try {
      const result = await apiPost("/bots/seed/defaults", {});
      setStatus(`Seeded ${result.bot_count} default bots across ${result.market_count} markets.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleResetArena() {
    const confirmed = window.confirm("Reset the bot arena? This clears bot users, bot runs, and arena markets.");
    if (!confirmed) {
      return;
    }
    setError("");
    setStatus("");
    try {
      await apiPost("/bots/arena/reset", {});
      setStatus("Bot arena reset.");
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleScheduler(action) {
    setError("");
    setStatus("");
    try {
      const result = await apiPost(`/bots/scheduler/${action}`, {});
      setScheduler(result);
      setStatus(`Bot scheduler ${result.running ? "running" : "stopped"}.`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRunCycle() {
    setError("");
    setStatus("");
    try {
      const payload = botRunMarketSlug ? { trigger_source: "manual", market_slug: botRunMarketSlug } : { trigger_source: "manual" };
      const result = await apiPost("/bots/run-cycle", payload);
      setStatus(`Ran bot cycle. ${result.length} bot evaluations were logged.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRunBot(botId) {
    setError("");
    setStatus("");
    try {
      const targetMarketSlug = botRunMarketSlug || markets[0]?.slug;
      if (!targetMarketSlug) {
        throw new Error("Create or seed a market before running bots.");
      }
      const result = await apiPost(`/bots/${botId}/run`, { trigger_source: "manual", market_slug: targetMarketSlug });
      setStatus(`Ran ${bots.find((bot) => bot.id === botId)?.display_name || `bot #${botId}`} on ${targetMarketSlug}: ${result.action_type}.`);
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="grid two">
      <section className="panel stack">
        <h1>Admin</h1>
        <p className="muted">Admin pages require an admin-tier account.</p>
        {status ? <p className="notice">{status}</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <article className="market-card">
          <strong>Seed demo markets</strong>
          <span className="muted">
            Creates the full starter catalog for Arctic sea ice, ENSO, earthquakes, and solar flares.
          </span>
          <span className="muted">
            Recommended for a fresh arena because it creates markets and links them to the right pipeline series in one step.
          </span>
          <span className="muted">
            Volcano history backfill is separate: use the Smithsonian card below to clean bad legacy rows and pull archived weekly counts for charts.
          </span>
          <button className="btn primary" onClick={handleSeedDemoMarkets} type="button">
            Seed demo markets
          </button>
          {demoSeedSummary?.pipelines?.map((pipeline) => (
            <span className="muted" key={pipeline.source_key}>
              {pipeline.pipeline_label}: +{pipeline.created_markets} markets, {pipeline.existing_markets} existing, +{pipeline.created_links} links
            </span>
          ))}
        </article>
        <article className="market-card">
          <strong>Refresh all datasets</strong>
          <span className="muted">Runs each science pipeline sequentially and keeps any successful refreshes even if another pipeline fails.</span>
          <button className="btn primary" onClick={handleFetchAllPipelines} type="button">
            Fetch all datasets
          </button>
          {fetchAllResults.map((result) => (
            <span className={result.status === "success" ? "muted" : "error"} key={result.source_key}>
              {result.label}: {result.status}
              {result.status === "success"
                ? ` (${result.inserted_points} new / ${result.received_points} received)`
                : result.error_message
                  ? ` - ${result.error_message}`
                  : ""}
            </span>
          ))}
        </article>
        {INGEST_CONTROLS.map((control) => (
          <article className="market-card" key={control.key}>
            <strong>{control.label}</strong>
            <span className="muted">{control.key}</span>
            <span>{control.description}</span>
            <div className="actions">
              <button className="btn secondary" onClick={() => handleFetchPipeline(control)} type="button">
                Fetch latest data
              </button>
              {control.backfillPath ? (
                <button className="btn secondary" onClick={() => handleBackfillVolcanoHistory(control)} type="button">
                  Backfill history
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Create market</h2>
        <article className="market-card">
          <strong>How to create and link a demo market</strong>
          <span className="muted">1. Create the market with a pipeline-specific category like arctic systems, enso outlook, earthquakes, or solar flares.</span>
          <span className="muted">2. In the market card below, use Data link to attach the right source and series for resolution.</span>
          <span className="muted">Arctic: `nsidc_charctic_daily` + `daily_extent_million_sq_km`</span>
          <span className="muted">Antarctic: `nsidc_antarctic_daily` + `daily_extent_million_sq_km`</span>
          <span className="muted">ENSO: `enso_oni` + `oni_index` by default, or `roni_index` for Relative ONI markets</span>
          <span className="muted">Earthquakes: `usgs_earthquakes` + `earthquake_magnitude`</span>
          <span className="muted">Solar flares: `nasa_donki_solar_flares` + `solar_flare_intensity`</span>
          <span className="muted">Volcanoes: `smithsonian_volcanoes` + `weekly_eruption_count` or `active_volcano_count`</span>
        </article>
        <article className="market-card">
          <strong>Quick templates</strong>
          <div className="actions">
            {MARKET_TEMPLATES.map((template) => (
              <button className="btn secondary" key={template.key} onClick={() => applyTemplate(template)} type="button">
                {template.label}
              </button>
            ))}
          </div>
        </article>
        <form className="stack" onSubmit={handleCreateMarket}>
          <label className="field">
            <span>Slug</span>
            <input value={market.slug} onChange={(event) => setMarket({ ...market, slug: event.target.value })} />
          </label>
          <label className="field">
            <span>Title</span>
            <input value={market.title} onChange={(event) => setMarket({ ...market, title: event.target.value })} />
          </label>
          <label className="field">
            <span>Category</span>
            <input value={market.category} onChange={(event) => setMarket({ ...market, category: event.target.value })} />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea value={market.description} onChange={(event) => setMarket({ ...market, description: event.target.value })} />
          </label>
          <label className="field">
            <span>Resolution criteria</span>
            <textarea
              value={market.resolution_criteria}
              onChange={(event) => setMarket({ ...market, resolution_criteria: event.target.value })}
            />
          </label>
          <label className="field">
            <span>Close date</span>
            <input
              type="datetime-local"
              value={market.close_at}
              onChange={(event) => setMarket({ ...market, close_at: event.target.value })}
            />
          </label>
          <label className="field">
            <span>Outcomes</span>
            <input value={market.outcomes} onChange={(event) => setMarket({ ...market, outcomes: event.target.value })} />
          </label>
          <label className="field">
            <span>LMSR b</span>
            <input value={market.b} onChange={(event) => setMarket({ ...market, b: event.target.value })} />
          </label>
          <button className="btn primary" type="submit">
            Create market
          </button>
        </form>
      </section>

      <section className="panel stack">
        <h2>Bot arena</h2>
        <article className="market-card">
          <strong>How to operate the bot arena</strong>
          <span className="muted">Seed default bots: creates the visible bot personas, user accounts, and funded wallets.</span>
          <span className="muted">Run cycle now: evaluates every active bot against the target market slug or all open markets if blank.</span>
          <span className="muted">Start scheduler: keeps evaluating bots automatically on their configured cadence.</span>
          <span className="muted">Stop scheduler: pauses automatic evaluation without deleting bots, positions, or run history.</span>
          <span className="muted">Reset arena: clears bot users, bot runs, and arena market state for a clean restart.</span>
          <span className="muted">Run bot now: evaluates one specific bot against the target market slug shown in this panel.</span>
        </article>
        <article className="market-card">
          <strong>Example workflows</strong>
          <span className="muted">Fresh arena: Seed demo markets -&gt; Fetch latest data -&gt; Seed default bots -&gt; Run cycle now -&gt; Start scheduler.</span>
          <span className="muted">Manual ENSO market: Create market with category `enso outlook` -&gt; link `enso_oni` / `oni_index` -&gt; Fetch latest data -&gt; Run cycle now.</span>
          <span className="muted">Volcano market: Seed demo markets -&gt; Fetch Smithsonian volcanoes -&gt; Run cycle now -&gt; inspect theses for event-chasing bots.</span>
          <span className="muted">One-off bot check: enter a target market slug, click Run bot now on a persona, then inspect the recent thesis and action summary.</span>
        </article>
        <span className="muted">
          Scheduler: {scheduler.running ? "running" : "stopped"} · Poll interval: {scheduler.poll_interval_seconds}s
        </span>
        <span className="muted">
          Last tick: {scheduler.last_tick_at ? new Date(scheduler.last_tick_at).toLocaleString() : "No ticks yet"}
        </span>
        <label className="field">
          <span>Target market slug</span>
          <input
            placeholder={markets[0]?.slug || "Seed markets first"}
            value={botRunMarketSlug}
            onChange={(event) => setBotRunMarketSlug(event.target.value)}
          />
        </label>
        <div className="actions">
          <button className="btn primary" onClick={handleSeedBots} type="button">
            Seed default bots
          </button>
          <button className="btn secondary" onClick={handleRunCycle} type="button">
            Run cycle now
          </button>
          <button className="btn secondary" onClick={() => handleScheduler("start")} type="button">
            Start scheduler
          </button>
          <button className="btn secondary" onClick={() => handleScheduler("stop")} type="button">
            Stop scheduler
          </button>
          <button className="btn danger" onClick={handleResetArena} type="button">
            Reset arena
          </button>
        </div>
        {bots.length === 0 ? <p className="muted">No bot profiles yet.</p> : null}
        {bots.map((bot) => (
          <article className="market-card" key={bot.id}>
            <strong>{bot.display_name}</strong>
            <span>
              {bot.strategy_type} · {bot.status}
            </span>
            <span className="muted">{bot.email}</span>
            <span>{bot.persona}</span>
            <span>
              Wallet: {bot.wallet_balance.toFixed(2)} · Max trade: {bot.max_trade_amount.toFixed(2)} · Max exposure:{" "}
              {bot.max_market_exposure.toFixed(2)}
            </span>
            <span className="muted">Last run: {bot.last_ran_at ? new Date(bot.last_ran_at).toLocaleString() : "Never"}</span>
            <div className="actions">
              <button className="btn secondary" onClick={() => handleRunBot(bot.id)} type="button">
                Run bot now
              </button>
            </div>
            {bot.recent_runs?.slice(0, 3).map((run) => (
              <div className="stack" key={run.id}>
                <span>
                  {run.market_slug || "No market"} · {run.action_type} · {run.status}
                </span>
                {run.outcome ? <span>Outcome: {run.outcome}</span> : null}
                {run.shares ? <span>Shares: {run.shares.toFixed(2)}</span> : null}
                {run.thesis_summary ? <span className="muted">{run.thesis_summary}</span> : null}
                {run.error_message ? <span className="error">{run.error_message}</span> : null}
              </div>
            ))}
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Mint wallet</h2>
        <p className="muted">Use this local admin tool as the current stand-in for Terracoin purchases.</p>
        <form className="stack" onSubmit={handleMint}>
          <label className="field">
            <span>User ID</span>
            <input value={mint.user_id} onChange={(event) => setMint({ ...mint, user_id: event.target.value })} />
          </label>
          <label className="field">
            <span>Amount</span>
            <input value={mint.amount} onChange={(event) => setMint({ ...mint, amount: event.target.value })} />
          </label>
          <label className="field">
            <span>Memo</span>
            <input value={mint.memo} onChange={(event) => setMint({ ...mint, memo: event.target.value })} />
          </label>
          <button className="btn primary" type="submit">
            Mint Terracoin
          </button>
        </form>
      </section>

      <section className="panel stack">
        <h2>Resolve markets</h2>
        {markets.length === 0 ? <p className="muted">No markets available.</p> : null}
        {markets.map((item) => (
          <article className="market-card" key={item.slug}>
            <strong>{item.title}</strong>
            <span className="market-meta">{item.slug}</span>
            <span>Category: {item.category}</span>
            <span>Status: {item.status}</span>
            <span>Closes: {new Date(item.close_at).toLocaleString()}</span>
            {item.resolved_outcome ? <span>Resolved outcome: {item.resolved_outcome}</span> : null}
            <div className="actions">
              <select
                disabled={item.status !== "open"}
                value={resolveSelections[item.slug] || item.outcomes[0] || ""}
                onChange={(event) =>
                  setResolveSelections((current) => ({ ...current, [item.slug]: event.target.value }))
                }
              >
                {item.outcomes.map((outcome) => (
                  <option key={outcome} value={outcome}>
                    {outcome}
                  </option>
                ))}
              </select>
              <button
                className="btn danger"
                disabled={item.status !== "open"}
                onClick={() => handleResolveMarket(item.slug)}
                type="button"
              >
                Resolve
              </button>
              <Link className="btn" href={`/markets/${item.slug}`}>
                Open details
              </Link>
            </div>
            <div className="stack">
              <strong>Data link</strong>
              <label className="field">
                <span>Source key</span>
                <input
                  value={linkDrafts[item.slug]?.source_key || ""}
                  onChange={(event) =>
                    setLinkDrafts((current) => ({
                      ...current,
                      [item.slug]: { ...current[item.slug], source_key: event.target.value },
                    }))
                  }
                />
              </label>
              <label className="field">
                <span>Series key</span>
                <input
                  value={linkDrafts[item.slug]?.series_key || ""}
                  onChange={(event) =>
                    setLinkDrafts((current) => ({
                      ...current,
                      [item.slug]: { ...current[item.slug], series_key: event.target.value },
                    }))
                  }
                />
              </label>
              <button className="btn secondary" onClick={() => handleCreateLink(item.slug)} type="button">
                Link market data
              </button>
            </div>
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Purchase requests</h2>
        {purchaseRequests.length === 0 ? <p className="muted">No purchase requests yet.</p> : null}
        {purchaseRequests.map((request) => (
          <article className="market-card" key={request.id}>
            <strong>Request #{request.id}</strong>
            <span>User ID: {request.user_id}</span>
            <span>Amount: {request.amount.toFixed(2)} Terracoin</span>
            <span>Status: {request.status}</span>
            <span className="muted">{request.note || "No note"}</span>
            {request.status === "pending" ? (
              <button className="btn primary" onClick={() => handleApprovePurchaseRequest(request.id)} type="button">
                Approve request
              </button>
            ) : null}
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Data refresh requests</h2>
        {fetchRequests.length === 0 ? <p className="muted">No data refresh requests yet.</p> : null}
        {fetchRequests.map((request) => (
          <article className="market-card" key={request.id}>
            <strong>{request.label}</strong>
            <span>
              {request.source_key} · {request.status}
            </span>
            <span className="muted">
              Requested by {request.requested_by_email || `user #${request.requested_by_user_id}`}
            </span>
            <span className="muted">Created at {request.created_at}</span>
            {request.reviewed_at ? <span className="muted">Fulfilled at {request.reviewed_at}</span> : null}
            {request.note ? <span className="muted">{request.note}</span> : null}
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Users and wallets</h2>
        {users.length === 0 ? <p className="muted">No users loaded.</p> : null}
        {users.map((user) => (
          <article className="market-card" key={user.user_id}>
            <strong>{user.email}</strong>
            <span>User ID: {user.user_id}</span>
            <span>Tier: {user.tier}</span>
            <span>Wallet balance: {user.wallet_balance.toFixed(2)} Terracoin</span>
          </article>
        ))}
      </section>
    </div>
  );
}
