import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

export default function ProfilePage() {
  const [me, setMe] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [meData, walletData] = await Promise.all([apiGet("/auth/me"), apiGet("/wallet/detail")]);
        setMe(meData);
        setWallet(walletData);
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, []);

  if (error) {
    return <p className="error">{error}</p>;
  }

  if (!me || !wallet) {
    return <p className="muted">Loading profile...</p>;
  }

  return (
    <div className="grid two">
      <section className="panel stack">
        <h1>Profile</h1>
        <p>Email: {me.email}</p>
        <p>Tier: {me.tier}</p>
        <p>User ID: {me.id}</p>
      </section>
      <section className="panel stack">
        <h2>Wallet</h2>
        <p>Balance: {wallet.balance.toFixed(2)} Terracoin</p>
        <div className="actions">
          <Link className="btn secondary" href="/buy-terracoin">
            Buy Terracoin
          </Link>
          <Link className="btn" href="/portfolio">
            View portfolio
          </Link>
        </div>
        <div className="stack">
          <h3>Recent ledger</h3>
          {wallet.entries?.length ? (
            wallet.entries.slice(0, 8).map((entry) => (
              <article className="market-card" key={entry.id}>
                <strong>{entry.amount >= 0 ? `+${entry.amount.toFixed(2)}` : entry.amount.toFixed(2)} Terracoin</strong>
                <span>{entry.memo}</span>
                <span className="muted">{entry.created_at}</span>
              </article>
            ))
          ) : (
            <p className="muted">No wallet activity yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}
