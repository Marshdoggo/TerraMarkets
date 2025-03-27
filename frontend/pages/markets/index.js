// pages/markets/index.js
import { useEffect, useState } from 'react';

export default function MarketsIndexPage() {
  const [markets, setMarkets] = useState([]);

  useEffect(() => {
    fetch('http://localhost:8000/markets')
      .then(res => res.json())
      .then(data => setMarkets(data))
      .catch(err => console.error('Error fetching markets:', err));
  }, []);

  return (
    <div>
      <h1>All Markets</h1>
      {markets.length === 0 ? (
        <p>No markets yet or still loading...</p>
      ) : (
        <ul>
          {markets.map((m) => (
            <li key={m.id}>
              {m.question} (ID: {m.id})
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}