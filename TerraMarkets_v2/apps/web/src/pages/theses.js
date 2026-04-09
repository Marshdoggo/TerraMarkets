import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import CitationList from "../components/CitationList";
import { apiGet } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

function formatPercent(value) {
  return value === null || value === undefined ? "n/a" : `${(value * 100).toFixed(0)}%`;
}

function formatGroupLabel(thesis, groupBy) {
  if (groupBy === "bot") {
    return thesis.bot_display_name || "Unknown bot";
  }
  if (groupBy === "market") {
    return thesis.market_title || thesis.market_slug || "Unknown market";
  }
  return "Latest theses";
}

function ThesisCard({ thesis }) {
  return (
    <article className="market-card stack" key={thesis.id}>
      <strong>{thesis.market_title || thesis.market_slug || "Unknown market"}</strong>
      <span className="muted">
        {thesis.bot_display_name || "Unknown bot"}
        {thesis.strategy_type ? ` · ${thesis.strategy_type.replaceAll("_", " ")}` : ""}
      </span>
      <span>
        {thesis.action_type}
        {thesis.outcome ? ` ${thesis.outcome}` : ""} · Confidence {formatPercent(thesis.confidence)}
      </span>
      {thesis.shares ? <span>Shares: {thesis.shares.toFixed(2)}</span> : null}
      {thesis.thesis_summary ? <p className="muted">{thesis.thesis_summary}</p> : null}
      <CitationList citations={thesis.citations || []} title="Sources" />
      <div className="actions">
        {thesis.market_slug ? (
          <Link className="btn secondary" href={`/markets/${thesis.market_slug}`}>
            Open market
          </Link>
        ) : null}
        {thesis.bot_profile_id ? (
          <Link className="btn secondary" href={`/bots/${thesis.bot_profile_id}`}>
            Open bot
          </Link>
        ) : null}
      </div>
      <span className="muted">{new Date(thesis.finished_at || thesis.started_at).toLocaleString()}</span>
    </article>
  );
}

export default function ThesisFeedPage() {
  const [theses, setTheses] = useState([]);
  const [error, setError] = useState("");
  const [groupBy, setGroupBy] = useState("none");
  const [selectedBot, setSelectedBot] = useState("all");
  const [selectedMarket, setSelectedMarket] = useState("all");

  useEffect(() => {
    apiGet("/bots/public/theses")
      .then((payload) => setTheses(payload.theses || []))
      .catch((err) => setError(err.message));
  }, []);

  const botOptions = useMemo(() => {
    const seen = new Map();
    theses.forEach((thesis) => {
      const key = thesis.bot_profile_id ? String(thesis.bot_profile_id) : thesis.bot_display_name || "unknown";
      if (!seen.has(key)) {
        seen.set(key, {
          value: key,
          label: thesis.bot_display_name || "Unknown bot",
        });
      }
    });
    return Array.from(seen.values()).sort((left, right) => left.label.localeCompare(right.label));
  }, [theses]);

  const marketOptions = useMemo(() => {
    const seen = new Map();
    theses.forEach((thesis) => {
      const key = thesis.market_slug || thesis.market_title || "unknown";
      if (!seen.has(key)) {
        seen.set(key, {
          value: key,
          label: thesis.market_title || thesis.market_slug || "Unknown market",
        });
      }
    });
    return Array.from(seen.values()).sort((left, right) => left.label.localeCompare(right.label));
  }, [theses]);

  const filteredTheses = useMemo(() => {
    return theses.filter((thesis) => {
      const botKey = thesis.bot_profile_id ? String(thesis.bot_profile_id) : thesis.bot_display_name || "unknown";
      const marketKey = thesis.market_slug || thesis.market_title || "unknown";
      if (selectedBot !== "all" && botKey !== selectedBot) {
        return false;
      }
      if (selectedMarket !== "all" && marketKey !== selectedMarket) {
        return false;
      }
      return true;
    });
  }, [selectedBot, selectedMarket, theses]);

  const groupedTheses = useMemo(() => {
    if (groupBy === "none") {
      return [{ key: "all", label: "Latest theses", items: filteredTheses }];
    }
    const groups = new Map();
    filteredTheses.forEach((thesis) => {
      const key = groupBy === "bot"
        ? (thesis.bot_profile_id ? String(thesis.bot_profile_id) : thesis.bot_display_name || "unknown")
        : (thesis.market_slug || thesis.market_title || "unknown");
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          label: formatGroupLabel(thesis, groupBy),
          items: [],
        });
      }
      groups.get(key).items.push(thesis);
    });
    return Array.from(groups.values()).sort((left, right) => left.label.localeCompare(right.label));
  }, [filteredTheses, groupBy]);

  return (
    <div className="stack">
      <section className="hero stack">
        <p className="muted">Cross-market commentary feed</p>
        <h1>Bot Theses</h1>
        <p>Browse the latest thesis stream across the whole TerraMarkets observatory, then narrow it by bot, by market, or group it into cleaner sections.</p>
      </section>
      {error ? <p className="error">{error}</p> : null}
      <section className="panel stack">
        <strong>Browse theses</strong>
        <div className="grid two">
          <label className="field">
            <span>Group by</span>
            <select value={groupBy} onChange={(event) => setGroupBy(event.target.value)}>
              <option value="none">Newest first</option>
              <option value="bot">Bot</option>
              <option value="market">Market</option>
            </select>
          </label>
          <label className="field">
            <span>Filter by bot</span>
            <select value={selectedBot} onChange={(event) => setSelectedBot(event.target.value)}>
              <option value="all">All bots</option>
              {botOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Filter by market</span>
            <select value={selectedMarket} onChange={(event) => setSelectedMarket(event.target.value)}>
              <option value="all">All markets</option>
              {marketOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <span className="muted">{filteredTheses.length} theses in the current view.</span>
      </section>
      {filteredTheses.length === 0 ? <p className="muted">No theses match the current filters. Try clearing one of the menus.</p> : null}
      {groupedTheses.map((group) => (
        <section className="stack" key={group.key}>
          {groupBy !== "none" ? (
            <div className="stack">
              <h2>{group.label}</h2>
              <span className="muted">{group.items.length} theses</span>
            </div>
          ) : null}
          {group.items.map((thesis) => (
            <ThesisCard key={thesis.id} thesis={thesis} />
          ))}
        </section>
      ))}
    </div>
  );
}
