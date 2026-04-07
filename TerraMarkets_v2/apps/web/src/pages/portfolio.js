import { useEffect, useState } from "react";

import { apiGet } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet("/portfolio")
      .then(setPortfolio)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return <p className="error">{error}</p>;
  }

  if (!portfolio) {
    return <p className="muted">Loading portfolio...</p>;
  }

  return (
    <div className="stack">
      <section className="hero stack">
        <h1>Portfolio</h1>
        <p className="muted">Wallet balance: {portfolio.wallet_balance.toFixed(2)} Terracoin</p>
        <div className="grid two">
          <div className="panel stack">
            <strong>Cost basis</strong>
            <span>{portfolio.total_cost_basis.toFixed(2)} Terracoin</span>
          </div>
          <div className="panel stack">
            <strong>Current value</strong>
            <span>{portfolio.total_current_value.toFixed(2)} Terracoin</span>
          </div>
          <div className="panel stack">
            <strong>Unrealized P/L</strong>
            <span>{portfolio.total_unrealized_pl.toFixed(2)} Terracoin</span>
          </div>
          <div className="panel stack">
            <strong>Settled winnings</strong>
            <span>{portfolio.settled_winnings.toFixed(2)} Terracoin</span>
          </div>
        </div>
      </section>

      <section className="panel stack">
        <h2>Open Positions</h2>
        {portfolio.open_positions.length === 0 ? <p className="muted">No open positions yet.</p> : null}
        {portfolio.open_positions.map((position) => (
          <article className="market-card" key={`${position.market_id}-${position.outcome}`}>
            <strong>{position.market_title}</strong>
            <span className="market-meta">{position.market_slug}</span>
            <span>Outcome: {position.outcome}</span>
            <span>Shares: {position.shares.toFixed(2)}</span>
            <span>Status: {position.market_status}</span>
            <span>Cost basis: {position.cost_basis.toFixed(2)} Terracoin</span>
            <span>
              Current price: {position.current_price !== null ? `${(position.current_price * 100).toFixed(2)}%` : "n/a"}
            </span>
            <span>
              Current value: {position.current_value !== null ? `${position.current_value.toFixed(2)} Terracoin` : "n/a"}
            </span>
            <span>
              Unrealized P/L: {position.unrealized_pl !== null ? `${position.unrealized_pl.toFixed(2)} Terracoin` : "n/a"}
            </span>
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Settled Positions</h2>
        {portfolio.settled_positions.length === 0 ? <p className="muted">No settled positions yet.</p> : null}
        {portfolio.settled_positions.map((position) => (
          <article className="market-card" key={`settled-${position.market_id}-${position.outcome}`}>
            <strong>{position.market_title}</strong>
            <span className="market-meta">{position.market_slug}</span>
            <span>Outcome held: {position.outcome}</span>
            <span>Shares: {position.shares.toFixed(2)}</span>
            <span>Resolved outcome: {position.resolved_outcome}</span>
            <span>Cost basis: {position.cost_basis.toFixed(2)} Terracoin</span>
            <span>
              Settlement value: {position.settlement_value !== null ? `${position.settlement_value.toFixed(2)} Terracoin` : "n/a"}
            </span>
            <span>
              Realized P/L: {position.realized_pl !== null ? `${position.realized_pl.toFixed(2)} Terracoin` : "n/a"}
            </span>
          </article>
        ))}
      </section>

      <section className="panel stack">
        <h2>Order History</h2>
        {portfolio.orders.length === 0 ? <p className="muted">No orders yet.</p> : null}
        {portfolio.orders.map((order) => (
          <article className="market-card" key={order.order_id}>
            <strong>{order.market_title}</strong>
            <span className="market-meta">{order.market_slug}</span>
            <span>
              Bought {order.shares.toFixed(2)} {order.outcome} shares
            </span>
            <span>Cost: {order.cost.toFixed(2)} Terracoin</span>
            <span>Average price: {(order.avg_price * 100).toFixed(2)}%</span>
            <span className="muted">{order.created_at}</span>
          </article>
        ))}
      </section>
    </div>
  );
}
