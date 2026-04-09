import Link from "next/link";
import { useEffect, useState } from "react";
import { getAccessToken, logoutSession } from "../lib/api";

export default function NavBar() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(Boolean(getAccessToken()));
  }, []);

  async function handleLogout() {
    await logoutSession();
    setIsLoggedIn(false);
    window.location.href = "/";
  }

  return (
    <nav className="nav">
      <div className="nav-links">
        <Link className="brand" href="/">
          TerraMarkets_v2
        </Link>
        <Link href="/markets">Markets</Link>
        <Link href="/datasets">Datasets</Link>
        <Link href="/bots">Bot Observatory</Link>
        <Link href="/theses">Theses</Link>
        <Link href="/profile">Profile</Link>
        <Link href="/portfolio">Portfolio</Link>
        <Link href="/buy-terracoin">Buy Terracoin</Link>
        <Link href="/data-lab">Data Lab</Link>
        <Link href="/admin">Admin</Link>
      </div>
      <div className="nav-actions">
        {isLoggedIn ? (
          <button className="btn" onClick={handleLogout}>
            Logout
          </button>
        ) : (
          <>
            <Link href="/login">Login</Link>
            <Link href="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}
