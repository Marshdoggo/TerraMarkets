import { useState } from "react";

import { apiPost } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

const PRESET_AMOUNTS = [100, 250, 500, 1000];

export default function BuyTerracoinPage() {
  const [amount, setAmount] = useState("250");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function handlePurchase(event) {
    event.preventDefault();
    setStatus("");
    setError("");
    try {
      const purchaseRequest = await apiPost("/wallet/purchase-requests", {
        amount: Number(amount),
        note: `Local Terracoin purchase request for ${amount}`,
      });
      setStatus(`Purchase request #${purchaseRequest.id} recorded for ${Number(amount).toFixed(2)} Terracoin.`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="grid two">
      <section className="panel stack">
        <h1>Buy Terracoin</h1>
        <p className="muted">
          This local flow now records a purchase request instead of instantly minting credits. Admins can review and approve requests from the admin screen.
        </p>
        <div className="actions">
          {PRESET_AMOUNTS.map((preset) => (
            <button className="btn secondary" key={preset} onClick={() => setAmount(String(preset))} type="button">
              {preset}
            </button>
          ))}
        </div>
      </section>

      <section className="panel stack">
        {status ? <p className="notice">{status}</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <form className="stack" onSubmit={handlePurchase}>
          <label className="field">
            <span>Terracoin amount</span>
            <input min="1" step="1" type="number" value={amount} onChange={(event) => setAmount(event.target.value)} />
          </label>
          <button className="btn primary" type="submit">
            Submit purchase request
          </button>
        </form>
      </section>
    </div>
  );
}
