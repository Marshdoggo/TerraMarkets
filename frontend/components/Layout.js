// components/Layout.js
import NavBar from './NavBar';

export default function Layout({ children }) {
  return (
    <div className="layout-container">
      <header>My Existing Header</header>

      {/* Our new NavBar component */}
      <NavBar />

      {/* The main content area for each page */}
      <main>{children}</main>

      <footer>My Existing Footer</footer>
    </div>
  );
}