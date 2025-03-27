// pages/markets/[id].js
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

export default function MarketDetailsPage() {
  const router = useRouter();
  const { id } = router.query;
  const [market, setMarket] = useState(null);

  useEffect(() => {
    if (id) {
      fetch(`http://localhost:8000/markets/${id}`)
        .then(res => res.json())
        .then(data => setMarket(data));
    }
  }, [id]);

  if (!market) {
    return <p>Loading market data...</p>;
  }

  return (
    <div>
      <h1>Market Details for {market.id}</h1>
      <p>{market.question}</p>
    </div>
  );
}