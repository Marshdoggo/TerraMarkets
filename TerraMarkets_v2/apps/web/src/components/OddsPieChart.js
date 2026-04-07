function polarToCartesian(centerX, centerY, radius, angleInDegrees) {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  };
}

function describeArc(centerX, centerY, radius, startAngle, endAngle) {
  const start = polarToCartesian(centerX, centerY, radius, endAngle);
  const end = polarToCartesian(centerX, centerY, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return [
    "M",
    centerX,
    centerY,
    "L",
    start.x,
    start.y,
    "A",
    radius,
    radius,
    0,
    largeArcFlag,
    0,
    end.x,
    end.y,
    "Z",
  ].join(" ");
}

const PIE_COLORS = ["#205c3b", "#6f8f76", "#d7b66f", "#b86c51", "#9f8dc5", "#5f7ea8"];

export default function OddsPieChart({ prices = {}, size = 220 }) {
  const entries = Object.entries(prices)
    .map(([label, value]) => ({ label, value: Number(value) || 0 }))
    .filter((entry) => entry.value > 0);

  if (!entries.length) {
    return <div className="odds-pie-empty">No odds yet.</div>;
  }

  let currentAngle = 0;
  const radius = size / 2 - 8;
  const center = size / 2;

  return (
    <div className="odds-pie-wrap">
      <svg className="odds-pie-chart" viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Current market odds pie chart">
        {entries.map((entry, index) => {
          const sweep = entry.value * 360;
          const startAngle = currentAngle;
          const endAngle = currentAngle + sweep;
          currentAngle = endAngle;
          return (
            <path
              key={entry.label}
              d={describeArc(center, center, radius, startAngle, endAngle)}
              fill={PIE_COLORS[index % PIE_COLORS.length]}
              stroke="#fffaf0"
              strokeWidth="2"
            />
          );
        })}
        <circle cx={center} cy={center} r={radius * 0.45} fill="#fffaf0" />
        <text x={center} y={center - 6} textAnchor="middle" className="odds-pie-center-label">
          LMSR
        </text>
        <text x={center} y={center + 18} textAnchor="middle" className="odds-pie-center-value">
          odds
        </text>
      </svg>
      <div className="odds-pie-legend">
        {entries
          .slice()
          .sort((left, right) => right.value - left.value)
          .map((entry, index) => (
            <div className="odds-pie-legend-row" key={entry.label}>
              <span
                className="odds-pie-swatch"
                style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
                aria-hidden="true"
              />
              <span className="odds-pie-legend-label">{entry.label}</span>
              <strong>{(entry.value * 100).toFixed(1)}%</strong>
            </div>
          ))}
      </div>
    </div>
  );
}
