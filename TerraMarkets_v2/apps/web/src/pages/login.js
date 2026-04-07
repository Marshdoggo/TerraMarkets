import { useState } from "react";
import { useRouter } from "next/router";
import { apiPost, setTokens } from "../lib/api";
export { emptyServerProps as getServerSideProps } from "../lib/ssr";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const tokens = await apiPost("/auth/login", { email, password });
      setTokens(tokens);
      router.push("/profile");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="panel stack">
      <h1>Login</h1>
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
          Log in
        </button>
      </form>
    </div>
  );
}
