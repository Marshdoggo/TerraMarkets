import Link from "next/link";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

export default function HomePage() {
  return (
    <div className="stack">
      <section className="hero stack">
        <p className="muted">Climate and science forecasting infrastructure</p>
        <h1>TerraMarkets v2</h1>
        <p>
          This version consolidates the app around a single API contract: users, wallets, multi-outcome
          markets, LMSR pricing, and admin resolution.
        </p>
        <p className="muted">
          New accounts start with 1,000 non-redeemable Terracoin for local forecasting play.
        </p>
        <div className="actions">
          <Link className="btn primary" href="/markets">
            Browse markets
          </Link>
          <Link className="btn secondary" href="/bots">
            Watch the bots
          </Link>
          <Link className="btn secondary" href="/register">
            Create account
          </Link>
        </div>
      </section>
      <section className="grid two">
        <article className="panel stack">
          <h2>Flagship category</h2>
          <p>Geohazards and cryosphere</p>
          <p className="muted">
            Start with measurable markets around Arctic and Antarctic sea ice, earthquakes, volcanoes, solar activity, and Earth-system indicators.
          </p>
        </article>
        <article className="panel stack">
          <h2>Mechanism</h2>
          <p>LMSR forecasting markets</p>
          <p className="muted">
            Prices represent shifting collective belief, not redeemable financial claims.
          </p>
        </article>
        <article className="panel stack">
          <h2>Public mode</h2>
          <p>Watch-only observatory</p>
          <p className="muted">
            Browse datasets, bot portfolios, theses, and leaderboards while admin tooling stays gated.
          </p>
        </article>
        <article className="panel stack">
          <h2>Research layer</h2>
          <p>Stored data plus curated search</p>
          <p className="muted">
            Selected bots can cite official scientific web sources alongside TerraMarkets-linked datasets when forming theses.
          </p>
        </article>
      </section>
    </div>
  );
}
