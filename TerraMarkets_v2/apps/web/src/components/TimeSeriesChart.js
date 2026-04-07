import { useMemo, useState } from "react";

const DEFAULT_RANGE_OPTIONS = [
  { key: "14d", label: "2W", days: 14 },
  { key: "30d", label: "1M", days: 30 },
  { key: "90d", label: "3M", days: 90 },
  { key: "180d", label: "6M", days: 180 },
  { key: "365d", label: "1Y", days: 365 },
  { key: "all", label: "All", days: null },
];

function formatDateLabel(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatNumber(value) {
  return value.toFixed(3);
}

function formatWindowDays(days) {
  if (days >= 365 && days % 365 === 0) {
    const years = days / 365;
    return `${years} year${years === 1 ? "" : "s"}`;
  }
  if (days >= 30 && days % 30 === 0) {
    const months = days / 30;
    return `${months} month${months === 1 ? "" : "s"}`;
  }
  if (days >= 7 && days % 7 === 0) {
    const weeks = days / 7;
    return `${weeks} week${weeks === 1 ? "" : "s"}`;
  }
  return `${days} day${days === 1 ? "" : "s"}`;
}

export default function TimeSeriesChart({ points, ariaLabel, unit, presetRanges = DEFAULT_RANGE_OPTIONS, enableCustomRange = true }) {
  const [rangeKey, setRangeKey] = useState("all");
  const [customDays, setCustomDays] = useState(null);
  const [hoverIndex, setHoverIndex] = useState(null);

  const validPoints = useMemo(
    () => (points || []).filter((point) => point.numeric_value !== null),
    [points]
  );

  if (validPoints.length < 2) {
    return <p className="muted">Not enough stored points for a chart.</p>;
  }

  const earliestDate = new Date(validPoints[0].observed_at);
  const latestDate = new Date(validPoints[validPoints.length - 1].observed_at);
  const totalDays = Math.max(1, Math.ceil((latestDate - earliestDate) / (1000 * 60 * 60 * 24)));
  const sliderMaxDays = Math.max(2, totalDays);
  const sliderMinDays = Math.min(7, sliderMaxDays);

  const availableRanges = presetRanges.filter((option) => {
    if (option.days === null) {
      return true;
    }
    const cutoff = new Date(latestDate);
    cutoff.setDate(cutoff.getDate() - option.days);
    return validPoints.some((point) => new Date(point.observed_at) <= cutoff);
  });

  const activeRange = availableRanges.find((option) => option.key === rangeKey) || availableRanges[availableRanges.length - 1];
  const activeDays = rangeKey === "custom" ? Math.max(sliderMinDays, Math.min(sliderMaxDays, customDays || sliderMaxDays)) : activeRange.days;

  const displayedPoints =
    activeDays === null
      ? validPoints
      : validPoints.filter((point) => {
          const cutoff = new Date(latestDate);
          cutoff.setDate(cutoff.getDate() - activeDays);
          return new Date(point.observed_at) >= cutoff;
        });

  const chartPoints = displayedPoints.length >= 2 ? displayedPoints : validPoints;

  const width = 520;
  const height = 220;
  const paddingLeft = 56;
  const paddingRight = 18;
  const paddingTop = 18;
  const paddingBottom = 36;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const values = chartPoints.map((point) => point.numeric_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const stepX = chartWidth / Math.max(chartPoints.length - 1, 1);

  const getX = (index) => paddingLeft + index * stepX;
  const getY = (value) => paddingTop + (1 - (value - min) / range) * chartHeight;

  const line = chartPoints
    .map((point, index) => `${index === 0 ? "M" : "L"}${getX(index).toFixed(2)},${getY(point.numeric_value).toFixed(2)}`)
    .join(" ");

  const yTicks = [max, min + range / 2, min];
  const xTickIndexes = [0, Math.floor((chartPoints.length - 1) / 2), chartPoints.length - 1];
  const activeIndex = hoverIndex ?? chartPoints.length - 1;
  const activePoint = chartPoints[activeIndex];
  const activeX = getX(activeIndex);
  const activeY = getY(activePoint.numeric_value);

  function handleMouseMove(event) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const scaleX = width / bounds.width;
    const svgX = (event.clientX - bounds.left) * scaleX;
    const relativeX = svgX - paddingLeft;
    const clamped = Math.max(0, Math.min(chartWidth, relativeX));
    const index = Math.round(clamped / Math.max(stepX, 1));
    setHoverIndex(Math.max(0, Math.min(chartPoints.length - 1, index)));
  }

  return (
    <div className="stack">
      <div className="actions">
        {availableRanges.map((option) => (
          <button
            key={option.key}
            className={`btn ${rangeKey === option.key ? "primary" : "secondary"}`}
            onClick={() => {
              setRangeKey(option.key);
              setHoverIndex(null);
            }}
            type="button"
          >
            {option.label}
          </button>
        ))}
        {enableCustomRange ? (
          <button
            className={`btn ${rangeKey === "custom" ? "primary" : "secondary"}`}
            onClick={() => {
              setRangeKey("custom");
              setCustomDays((current) => current || sliderMaxDays);
              setHoverIndex(null);
            }}
            type="button"
          >
            Custom
          </button>
        ) : null}
      </div>
      {enableCustomRange && rangeKey === "custom" ? (
        <label className="field">
          <span>Custom window: {formatWindowDays(activeDays)}</span>
          <input
            type="range"
            min={sliderMinDays}
            max={sliderMaxDays}
            step="1"
            value={activeDays}
            onChange={(event) => {
              setCustomDays(Number(event.target.value));
              setHoverIndex(null);
            }}
          />
        </label>
      ) : null}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={ariaLabel}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverIndex(null)}
        style={{ width: "100%", display: "block" }}
      >
        <rect x="0" y="0" width={width} height={height} rx="16" fill="rgba(255,255,255,0.4)" />

        {yTicks.map((tick) => {
          const y = getY(tick);
          return (
            <g key={tick}>
              <line x1={paddingLeft} y1={y} x2={width - paddingRight} y2={y} stroke="rgba(15,23,42,0.12)" strokeWidth="1" />
              <text x={paddingLeft - 8} y={y + 4} textAnchor="end" fontSize="11" fill="rgba(15,23,42,0.7)">
                {formatNumber(tick)}
              </text>
            </g>
          );
        })}

        {xTickIndexes.map((index) => {
          const x = getX(index);
          return (
            <text key={`${index}-${chartPoints[index].observed_at}`} x={x} y={height - 10} textAnchor="middle" fontSize="11" fill="rgba(15,23,42,0.7)">
              {formatDateLabel(chartPoints[index].observed_at)}
            </text>
          );
        })}

        <path d={line} fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />

        <line x1={activeX} y1={paddingTop} x2={activeX} y2={height - paddingBottom} stroke="rgba(15,23,42,0.22)" strokeDasharray="4 4" />
        <circle cx={activeX} cy={activeY} r="4.5" fill="var(--accent)" stroke="white" strokeWidth="2" />

        <rect x={paddingLeft} y={paddingTop} width={chartWidth} height={chartHeight} fill="transparent" />
      </svg>
      <div className="actions muted">
        <span>{formatDateLabel(chartPoints[0].observed_at)}</span>
        <span>{formatDateLabel(chartPoints[chartPoints.length - 1].observed_at)}</span>
      </div>
      <div className="panel stack">
        <strong>Hover readout</strong>
        <span>
          {formatDateLabel(activePoint.observed_at)}: {formatNumber(activePoint.numeric_value)} {unit || activePoint.unit || ""}
        </span>
      </div>
    </div>
  );
}
