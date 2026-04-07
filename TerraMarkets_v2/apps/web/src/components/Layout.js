import NavBar from "./NavBar";

export default function Layout({ children }) {
  return (
    <div className="shell">
      <NavBar />
      <main className="container">{children}</main>
      <style jsx global>{`
        :root {
          --bg: #f5f1e8;
          --panel: #fffaf0;
          --ink: #1e2a22;
          --muted: #66756c;
          --accent: #205c3b;
          --accent-soft: #dbe7d7;
          --danger: #8d2e24;
          --border: #d7d1c4;
        }

        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          font-family: Georgia, "Times New Roman", serif;
          color: var(--ink);
          background:
            radial-gradient(circle at top left, rgba(32, 92, 59, 0.08), transparent 32%),
            linear-gradient(180deg, #f8f4ed 0%, #f2ebdf 100%);
        }

        a {
          color: inherit;
          text-decoration: none;
        }

        button,
        input,
        textarea,
        select {
          font: inherit;
        }

        .shell {
          min-height: 100vh;
        }

        .nav {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          padding: 1rem 1.5rem;
          border-bottom: 1px solid var(--border);
          background: rgba(255, 250, 240, 0.9);
          backdrop-filter: blur(12px);
          position: sticky;
          top: 0;
        }

        .nav-links,
        .nav-actions {
          display: flex;
          gap: 0.75rem;
          flex-wrap: wrap;
        }

        .brand {
          font-size: 1.1rem;
          font-weight: 700;
          letter-spacing: 0.04em;
        }

        .container {
          width: min(1040px, calc(100% - 2rem));
          margin: 0 auto;
          padding: 2rem 0 4rem;
        }

        .hero,
        .panel {
          background: var(--panel);
          border: 1px solid var(--border);
          border-radius: 18px;
          box-shadow: 0 16px 40px rgba(39, 44, 34, 0.08);
        }

        .hero {
          padding: 2rem;
        }

        .panel {
          padding: 1.5rem;
        }

        .stack {
          display: grid;
          gap: 1rem;
        }

        .grid {
          display: grid;
          gap: 1rem;
        }

        .grid.two {
          grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        }

        .market-card {
          display: grid;
          gap: 0.75rem;
          padding: 1.25rem;
          border-radius: 16px;
          border: 1px solid var(--border);
          background: rgba(255, 255, 255, 0.65);
        }

        .market-card-featured {
          align-content: start;
        }

        .market-odds-strip {
          display: flex;
          gap: 0.65rem;
          flex-wrap: wrap;
        }

        .odds-chip {
          min-width: 88px;
          padding: 0.7rem 0.85rem;
          border-radius: 14px;
          border: 1px solid rgba(32, 92, 59, 0.14);
          background: linear-gradient(180deg, rgba(32, 92, 59, 0.12), rgba(32, 92, 59, 0.04));
          display: grid;
          gap: 0.2rem;
        }

        .odds-chip-label {
          color: var(--muted);
          font-size: 0.8rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .market-leading-odds {
          font-weight: 600;
          color: var(--accent);
        }

        .market-odds-panel {
          display: grid;
          gap: 1rem;
          padding: 1.2rem;
          border-radius: 18px;
          background: linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(219, 231, 215, 0.35));
          border: 1px solid rgba(32, 92, 59, 0.12);
        }

        .market-odds-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 0.75rem;
        }

        .odds-stat-card {
          display: grid;
          gap: 0.35rem;
          padding: 0.95rem 1rem;
          border-radius: 14px;
          background: rgba(255, 250, 240, 0.95);
          border: 1px solid var(--border);
        }

        .odds-stat-value {
          font-size: 1.6rem;
          line-height: 1;
          color: var(--accent);
        }

        .odds-pie-wrap {
          display: grid;
          gap: 1rem;
          justify-items: center;
        }

        .odds-pie-chart {
          width: min(220px, 100%);
          height: auto;
          filter: drop-shadow(0 10px 24px rgba(39, 44, 34, 0.08));
        }

        .odds-pie-center-label {
          font-size: 0.85rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          fill: var(--muted);
        }

        .odds-pie-center-value {
          font-size: 1rem;
          font-weight: 700;
          fill: var(--ink);
        }

        .odds-pie-legend {
          width: min(320px, 100%);
          display: grid;
          gap: 0.55rem;
        }

        .odds-pie-legend-row {
          display: grid;
          grid-template-columns: 14px 1fr auto;
          gap: 0.55rem;
          align-items: center;
          padding: 0.55rem 0.7rem;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.72);
          border: 1px solid rgba(32, 42, 34, 0.08);
        }

        .odds-pie-swatch {
          width: 14px;
          height: 14px;
          border-radius: 999px;
        }

        .odds-pie-legend-label {
          color: var(--muted);
        }

        .odds-pie-empty {
          color: var(--muted);
          padding: 1rem;
        }

        .market-meta,
        .muted {
          color: var(--muted);
        }

        .actions {
          display: flex;
          gap: 0.75rem;
          flex-wrap: wrap;
        }

        .btn {
          border: 1px solid var(--ink);
          background: transparent;
          color: var(--ink);
          border-radius: 999px;
          padding: 0.65rem 1rem;
          cursor: pointer;
        }

        .btn.primary {
          background: var(--accent);
          border-color: var(--accent);
          color: #f8fff7;
        }

        .btn.secondary {
          background: var(--accent-soft);
          border-color: var(--accent-soft);
        }

        .btn.danger {
          background: var(--danger);
          border-color: var(--danger);
          color: #fff7f5;
        }

        .field {
          display: grid;
          gap: 0.35rem;
        }

        .field input,
        .field textarea,
        .field select {
          width: 100%;
          padding: 0.8rem 0.9rem;
          border-radius: 12px;
          border: 1px solid var(--border);
          background: #fff;
        }

        .notice {
          padding: 0.8rem 1rem;
          border-radius: 12px;
          background: var(--accent-soft);
        }

        .error {
          padding: 0.8rem 1rem;
          border-radius: 12px;
          color: #fff;
          background: var(--danger);
        }

        .table-wrap {
          overflow-x: auto;
        }

        .table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.95rem;
        }

        .table th,
        .table td {
          text-align: left;
          padding: 0.6rem 0.5rem;
          border-bottom: 1px solid var(--border);
          vertical-align: top;
        }

        .table th {
          color: var(--muted);
          font-weight: 600;
        }

        @media (max-width: 640px) {
          .nav {
            align-items: flex-start;
            flex-direction: column;
          }

          .container {
            width: min(100% - 1rem, 1040px);
          }

          .market-odds-panel {
            padding: 1rem;
          }
        }
      `}</style>
    </div>
  );
}
