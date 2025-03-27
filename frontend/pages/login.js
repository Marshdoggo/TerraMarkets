// pages/login.js
import { useState } from 'react';
import { useRouter } from 'next/router';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const router = useRouter();

  async function handleLogin(e) {
    e.preventDefault();

    try {
      // This is how FastAPI expects OAuth2PasswordRequestForm data:
      // { username: '...', password: '...' }
      // Some frameworks also require "grant_type", "scope", etc.,
      // but your current FastAPI code may only need username + password.
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const res = await fetch('http://localhost:8000/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (!res.ok) {
        throw new Error('Login failed');
      }

      const data = await res.json();
      // data should be like: { "access_token": "...", "token_type": "bearer" }
      const token = data.access_token;

      // Store token in localStorage (simple approach)
      localStorage.setItem('accessToken', token);

      // Optionally redirect to profile or homepage
      router.push('/profile');

    } catch (err) {
      console.error(err);
      alert('Login failed. Check console for details.');
    }
  }

  return (
    <div>
      <h1>Login</h1>
      <form onSubmit={handleLogin}>
        <div>
          <label>Username:</label>
          <input
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
          />
        </div>
        <div>
          <label>Password:</label>
          <input
            value={password}
            onChange={e => setPassword(e.target.value)}
            type="password"
            required
          />
        </div>
        <button type="submit">Log In</button>
      </form>
    </div>
  );
}