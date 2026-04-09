import { useEffect, useMemo, useState } from "react";

import TimeSeriesChart from "../components/TimeSeriesChart";
import { apiGet, apiPost } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

const PIPELINE_CONTROLS = [
  {
    key: "nsidc_charctic_daily",
    label: "Arctic sea ice",
    description: "Fetches today plus the prior 365 days of NSIDC Arctic sea ice extent and appends only new observations.",
    fetchPath: "/data/fetch/nsidc-charctic",
    fetchBody: { days: 365 },
    requestLabel: "NSIDC Arctic sea ice extent refresh",
  },
  {
    key: "enso_oni",
    label: "ENSO / ONI",
    description: "Fetches the latest NOAA CPC ENSO table and appends only unseen monthly observations.",
    fetchPath: "/data/fetch/enso-oni",
    fetchBody: { source_key: "enso_oni" },
    requestLabel: "NOAA CPC ENSO refresh",
  },
  {
    key: "nsidc_antarctic_daily",
    label: "Antarctic sea ice",
    description: "Fetches the rolling 365-day NSIDC Antarctic extent series and appends only new observations.",
    fetchPath: "/data/fetch/nsidc-antarctic",
    fetchBody: { days: 365 },
    requestLabel: "NSIDC Antarctic sea ice extent refresh",
  },
  {
    key: "usgs_earthquakes",
    label: "USGS earthquakes",
    description: "Fetches the USGS monthly GeoJSON earthquake feed and appends only unseen events.",
    fetchPath: "/data/fetch/usgs-earthquakes",
    fetchBody: { source_key: "usgs_earthquakes" },
    requestLabel: "USGS earthquake feed refresh",
  },
  {
    key: "nasa_donki_solar_flares",
    label: "NASA DONKI solar flares",
    description: "Fetches the NASA DONKI solar flare feed and appends only unseen flare events.",
    fetchPath: "/data/fetch/donki-solar-flares",
    fetchBody: { source_key: "nasa_donki_solar_flares" },
    requestLabel: "NASA DONKI solar flare refresh",
  },
  {
    key: "smithsonian_volcanoes",
    label: "Smithsonian volcanoes",
    description: "Fetches the weekly Smithsonian volcanic activity report and appends derived eruption and active-volcano counts.",
    fetchPath: "/data/fetch/smithsonian-volcanoes",
    fetchBody: { source_key: "smithsonian_volcanoes" },
    backfillPath: "/data/fetch/smithsonian-volcanoes/backfill",
    backfillBody: { source_key: "smithsonian_volcanoes", weeks: 26, prune_invalid_existing: true },
    requestLabel: "Smithsonian weekly volcanic activity refresh",
  },
];

const DATASET_RANGE_PRESETS = {
  "nsidc_charctic_daily:daily_extent_million_sq_km": [
    { key: "30d", label: "1M", days: 30 },
    { key: "90d", label: "3M", days: 90 },
    { key: "365d", label: "1Y", days: 365 },
    { key: "3y", label: "3Y", days: 365 * 3 },
    { key: "all", label: "All", days: null },
  ],
  "nsidc_antarctic_daily:daily_extent_million_sq_km": [
    { key: "30d", label: "1M", days: 30 },
    { key: "90d", label: "3M", days: 90 },
    { key: "365d", label: "1Y", days: 365 },
    { key: "3y", label: "3Y", days: 365 * 3 },
    { key: "all", label: "All", days: null },
  ],
  "enso_oni:oni_index": [
    { key: "365d", label: "1Y", days: 365 },
    { key: "3y", label: "3Y", days: 365 * 3 },
    { key: "5y", label: "5Y", days: 365 * 5 },
    { key: "10y", label: "10Y", days: 365 * 10 },
    { key: "30y", label: "30Y", days: 365 * 30 },
    { key: "all", label: "All", days: null },
  ],
  "usgs_earthquakes:earthquake_magnitude": [
    { key: "1d", label: "1D", days: 1 },
    { key: "3d", label: "3D", days: 3 },
    { key: "7d", label: "1W", days: 7 },
    { key: "14d", label: "2W", days: 14 },
    { key: "30d", label: "1M", days: 30 },
    { key: "all", label: "All", days: null },
  ],
  "nasa_donki_solar_flares:solar_flare_intensity": [
    { key: "14d", label: "2W", days: 14 },
    { key: "30d", label: "1M", days: 30 },
    { key: "60d", label: "2M", days: 60 },
    { key: "90d", label: "3M", days: 90 },
    { key: "365d", label: "1Y", days: 365 },
    { key: "all", label: "All", days: null },
  ],
  "smithsonian_volcanoes:weekly_eruption_count": [
    { key: "30d", label: "1M", days: 30 },
    { key: "90d", label: "3M", days: 90 },
    { key: "365d", label: "1Y", days: 365 },
    { key: "all", label: "All", days: null },
  ],
  "smithsonian_volcanoes:active_volcano_count": [
    { key: "30d", label: "1M", days: 30 },
    { key: "90d", label: "3M", days: 90 },
    { key: "365d", label: "1Y", days: 365 },
    { key: "all", label: "All", days: null },
  ],
};

function buildDatasets(runs) {
  const datasets = new Map();

  runs.forEach((run) => {
    (run.points || []).forEach((point) => {
      const datasetKey = `${point.source_key}:${point.series_key}`;
      if (!datasets.has(datasetKey)) {
        datasets.set(datasetKey, {
          key: datasetKey,
          source_key: point.source_key,
          series_key: point.series_key,
          label: point.label,
          unit: point.unit,
          last_run_at: run.created_at,
          point_map: new Map(),
        });
      }

      const dataset = datasets.get(datasetKey);
      if (new Date(run.created_at) > new Date(dataset.last_run_at)) {
        dataset.last_run_at = run.created_at;
      }
      dataset.point_map.set(point.observed_at, point);
    });
  });

  return Array.from(datasets.values())
    .map((dataset) => {
      const points = Array.from(dataset.point_map.values()).sort(
        (left, right) => new Date(left.observed_at) - new Date(right.observed_at)
      );
      return {
        key: dataset.key,
        source_key: dataset.source_key,
        series_key: dataset.series_key,
        label: dataset.label,
        unit: dataset.unit,
        last_run_at: dataset.last_run_at,
        points,
        recent_points: [...points].reverse().slice(0, 5),
      };
    })
    .sort((left, right) => new Date(right.last_run_at) - new Date(left.last_run_at));
}

export default function DataLabPage() {
  const [runs, setRuns] = useState([]);
  const [me, setMe] = useState(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [fetchAllResults, setFetchAllResults] = useState([]);
  const [form, setForm] = useState({
    source_key: "nsidc_arctic_demo",
    summary: "Demo Arctic sea ice observation import",
    series_key: "sept_extent",
    label: "September sea ice extent",
    numeric_value: "4.12",
    unit: "million sq km",
    observed_at: "2026-09-15T00:00:00Z",
  });

  async function loadRuns() {
    try {
      const response = await apiGet("/data/runs");
      setRuns(response);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadMe() {
    try {
      const response = await apiGet("/auth/me");
      setMe(response);
    } catch {
      setMe(null);
    }
  }

  useEffect(() => {
    loadMe();
    loadRuns();
  }, []);

  const datasets = useMemo(() => buildDatasets(runs), [runs]);

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus("");
    setError("");
    try {
      await apiPost("/data/ingest", {
        source_key: form.source_key,
        summary: form.summary,
        payload: { mode: "demo" },
        points: [
          {
            series_key: form.series_key,
            label: form.label,
            numeric_value: Number(form.numeric_value),
            unit: form.unit,
            observed_at: form.observed_at,
            metadata_json: { entered_from: "data-lab" },
          },
        ],
      });
      setStatus("Data run stored.");
      await loadRuns();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleFetchPipeline(control) {
    setStatus("");
    setError("");
    try {
      const run = await apiPost(control.fetchPath, control.fetchBody);
      const inserted = run?.points?.length ?? 0;
      setStatus(`Fetched ${control.label}. ${inserted} new observations were appended.`);
      await loadRuns();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleFetchAllPipelines() {
    setStatus("");
    setError("");
    setFetchAllResults([]);
    try {
      const response = await apiPost("/data/fetch/all", {});
      setFetchAllResults(response.results || []);
      const succeeded = (response.results || []).filter((result) => result.status === "success").length;
      const failed = (response.results || []).filter((result) => result.status !== "success").length;
      setStatus(`Fetched all datasets. ${succeeded} succeeded, ${failed} failed.`);
      await loadRuns();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleBackfillVolcanoHistory(control) {
    setStatus("");
    setError("");
    try {
      const run = await apiPost(control.backfillPath, control.backfillBody);
      const inserted = run?.points?.length ?? 0;
      setStatus(`Backfilled ${control.label} history. ${inserted} observations were included in the backfill run.`);
      await loadRuns();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRequestFetch(control) {
    setStatus("");
    setError("");
    try {
      await apiPost("/data/fetch-requests", {
        source_key: control.key,
        label: control.requestLabel,
        note: `Requested from Data Lab by a non-admin user for ${control.label}.`,
      });
      setStatus(`Refresh request for ${control.label} sent to admins.`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="grid two">
      <section className="panel stack">
        <h1>Data Lab</h1>
        <p className="muted">
          Local admin surface for syncing fetched observations and reviewing each stored science dataset.
        </p>
        {status ? <p className="notice">{status}</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <div className="stack">
          <strong>Earth system pipelines</strong>
          {me?.tier === "admin" ? (
            <button className="btn primary" onClick={handleFetchAllPipelines} type="button">
              Fetch all datasets
            </button>
          ) : null}
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
          {PIPELINE_CONTROLS.map((control) => (
            <article className="market-card" key={control.key}>
              <strong>{control.label}</strong>
              <span className="muted">{control.key}</span>
              <span>{control.description}</span>
              {me?.tier === "admin" ? (
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
              ) : me ? (
                <button className="btn secondary" onClick={() => handleRequestFetch(control)} type="button">
                  Request refresh
                </button>
              ) : (
                <span className="muted">Sign in to request or run data refreshes.</span>
              )}
            </article>
          ))}
        </div>
        {me?.tier === "admin" ? (
          <form className="stack" onSubmit={handleSubmit}>
            <label className="field">
              <span>Source key</span>
              <input value={form.source_key} onChange={(event) => setForm({ ...form, source_key: event.target.value })} />
            </label>
            <label className="field">
              <span>Summary</span>
              <input value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} />
            </label>
            <label className="field">
              <span>Series key</span>
              <input value={form.series_key} onChange={(event) => setForm({ ...form, series_key: event.target.value })} />
            </label>
            <label className="field">
              <span>Label</span>
              <input value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} />
            </label>
            <label className="field">
              <span>Numeric value</span>
              <input value={form.numeric_value} onChange={(event) => setForm({ ...form, numeric_value: event.target.value })} />
            </label>
            <label className="field">
              <span>Unit</span>
              <input value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} />
            </label>
            <label className="field">
              <span>Observed at</span>
              <input value={form.observed_at} onChange={(event) => setForm({ ...form, observed_at: event.target.value })} />
            </label>
            <button className="btn primary" type="submit">
              Store demo observation
            </button>
          </form>
        ) : null}
      </section>

      <section className="panel stack">
        <h2>Stored datasets</h2>
        {datasets.length === 0 ? <p className="muted">No stored datasets yet.</p> : null}
        {datasets.map((dataset) => (
          <article className="market-card" key={dataset.key}>
            <strong>{dataset.label}</strong>
            <span className="muted">
              {dataset.source_key}:{dataset.series_key}
            </span>
            <span className="muted">Latest sync: {dataset.last_run_at}</span>
            <span>
              {dataset.points.length} stored observations across the current dataset history.
            </span>
            <TimeSeriesChart
              points={dataset.points}
              ariaLabel={`${dataset.label} time series`}
              unit={dataset.unit}
              presetRanges={DATASET_RANGE_PRESETS[dataset.key]}
              enableCustomRange
            />
            <div className="stack">
              <strong>Most recent 5 points</strong>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Observed</th>
                      <th>Label</th>
                      <th>Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dataset.recent_points.map((point) => (
                      <tr key={`${dataset.key}:${point.observed_at}`}>
                        <td>{point.observed_at.slice(0, 10)}</td>
                        <td>{point.label}</td>
                        <td>
                          {point.numeric_value ?? "n/a"} {point.unit || dataset.unit || ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
