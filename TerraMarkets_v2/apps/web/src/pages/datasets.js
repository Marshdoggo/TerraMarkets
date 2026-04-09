import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import TimeSeriesChart from "../components/TimeSeriesChart";
import { apiGet } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

function buildDatasets(runs) {
  const datasets = new Map();
  runs.forEach((run) => {
    (run.points || []).forEach((point) => {
      const key = `${point.source_key}:${point.series_key}`;
      if (!datasets.has(key)) {
        datasets.set(key, {
          key,
          label: point.label,
          source_key: point.source_key,
          series_key: point.series_key,
          unit: point.unit,
          point_map: new Map(),
          last_run_at: run.created_at,
        });
      }
      const dataset = datasets.get(key);
      dataset.point_map.set(point.observed_at, point);
      if (new Date(run.created_at) > new Date(dataset.last_run_at)) {
        dataset.last_run_at = run.created_at;
      }
    });
  });
  return Array.from(datasets.values())
    .map((dataset) => {
      const points = Array.from(dataset.point_map.values()).sort(
        (left, right) => new Date(left.observed_at) - new Date(right.observed_at)
      );
      return { ...dataset, points, recent_points: points.slice(-12) };
    })
    .sort((left, right) => new Date(right.last_run_at) - new Date(left.last_run_at));
}

export default function DatasetsPage() {
  const [runs, setRuns] = useState([]);
  const [error, setError] = useState("");
  const datasets = useMemo(() => buildDatasets(runs), [runs]);

  useEffect(() => {
    apiGet("/data/runs")
      .then(setRuns)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="stack">
      <section className="hero stack">
        <p className="muted">Public data observatory</p>
        <h1>Datasets</h1>
        <p>Browse the stored public-science datasets that TerraMarkets markets and bots are currently watching.</p>
      </section>
      {error ? <p className="error">{error}</p> : null}
      {datasets.length === 0 ? <p className="muted">No stored datasets yet.</p> : null}
      <div className="grid two">
        {datasets.map((dataset) => (
          <article className="market-card stack" key={dataset.key}>
            <strong>{dataset.label}</strong>
            <span className="muted">
              {dataset.source_key}:{dataset.series_key}
            </span>
            <span>Latest refresh: {new Date(dataset.last_run_at).toLocaleString()}</span>
            {dataset.points.length ? (
              <TimeSeriesChart points={dataset.recent_points} ariaLabel={`${dataset.label} recent history`} unit={dataset.unit} />
            ) : null}
            <span className="muted">Stored points: {dataset.points.length}</span>
            <div className="actions">
              <Link className="btn secondary" href="/data-lab">
                Open Data Lab
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
