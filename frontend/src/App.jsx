import React, { useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Batches from './pages/Batches';
import Verification from './pages/Verification';
import Demo from './pages/Demo';
import { fetchHealth } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="min-h-screen bg-navy-950">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} health={health} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard'    && <Dashboard health={health} />}
        {activeTab === 'batches'      && <Batches />}
        {activeTab === 'verification' && <Verification />}
        {activeTab === 'demo'         && <Demo />}
      </main>
    </div>
  );
}
