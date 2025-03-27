// pages/profile.js
import { useEffect, useState } from 'react';

export default function ProfilePage() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      // No token => not logged in
      return;
    }

    fetch('http://localhost:8000/me', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then(res => {
        if (!res.ok) {
          throw new Error('Failed to fetch profile');
        }
        return res.json();
      })
      .then(data => {
        setUser(data);
      })
      .catch(err => {
        console.error(err);
      });
  }, []);

  if (!user) {
    return <p>You are not logged in.</p>;
  }

  return (
    <div>
      <h1>Profile</h1>
      <p>ID: {user.id}</p>
      <p>Username: {user.username}</p>
      <p>Balance: {user.balance}</p>
    </div>
  );
}