// components/NavBar.js
import Link from 'next/link';

export default function NavBar() {
  return (
    <nav>
      <Link href="/">Home</Link> |{' '}
      <Link href="/profile">Profile</Link> |{' '}
      <Link href="/markets">Markets</Link> |{' '}
      <Link href="/login">Login</Link> |{' '}
      <Link href="/register">Register</Link>
    </nav>
  );
}