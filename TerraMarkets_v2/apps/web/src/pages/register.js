import { useState } from "react";
import { useRouter } from "next/router";
import { apiPost } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      await apiPost("/auth/register", { email, password });
      router.push("/login");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="panel stack">
      <h1>Create account</h1>
      <p className="muted">Each new account receives 1,000 non-redeemable Terracoin.</p>
      {error ? <p className="error">{error}</p> : null}
      <form className="stack" onSubmit={handleSubmit}>
        <label className="field">
          <span>Email</span>
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <button className="btn primary" type="submit">
          Register
        </button>
      </form>
    </div>
  );
}
