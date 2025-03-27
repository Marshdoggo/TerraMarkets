// pages/_app.js
import Layout from '../components/Layout';
import '../styles/global.css'; // (optional) If you want to add global CSS

function MyApp({ Component, pageProps }) {
  return (
    <Layout>
      {/* This is where the main page content goes */}
      <Component {...pageProps} />
    </Layout>
  );
}

export default MyApp;