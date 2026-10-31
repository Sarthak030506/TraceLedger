import React, { useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Batches from './pages/Batches';
import Verification from './pages/Verification';
import Demo from './pages/Demo';
import { usePath } from './router';
import { fetchHealth } from './services/api';

const APP_PAGES = {
  '/app': Dashboard,
  '/app/batches': Batches,
  '/app/verify': Verification,
  '/app/lab': Demo,
};

function AppShell({ path }) {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const Page = APP_PAGES[path.replace(/\/+$/, '')] || Dashboard;

  return (
    <div className="min-h-screen bg-paper text-ink">
      <Navbar path={path} health={health} />
      <main className="shell pb-24 pt-12 sm:pt-16">
        <Page health={health} />
      </main>
    </div>
  );
}

export default function App() {
  const path = usePath();
  if (path === '/app' || path.startsWith('/app/')) return <AppShell path={path} />;
  return <Landing />;
}
