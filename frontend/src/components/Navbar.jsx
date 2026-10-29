import React from 'react';
import { Shield, Layers, CheckSquare, Zap, Activity } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, health }) {
  const isOnline = health?.status === 'ok';

  return (
    <header className="sticky top-0 z-40 bg-navy-950/80 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-cyan-400 p-0.5 flex items-center justify-center glow-cyan shadow-lg shadow-cyan-500/20">
            <div className="w-full h-full bg-navy-950 rounded-[10px] flex items-center justify-center">
              <Shield className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white font-mono">TraceLedger</span>
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                MST Testnet
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Trust the evidence, not just the server
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 sm:gap-2">
          {[
            { id: 'dashboard', label: 'Overview', icon: Activity },
            { id: 'batches', label: 'Batches', icon: Layers },
            { id: 'verification', label: 'Verification', icon: CheckSquare },
            { id: 'demo', label: 'Attack Simulation', icon: Zap },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden md:inline">{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Connection Indicator */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-navy-850 border border-slate-700">
            <span
              className={`w-2 h-2 rounded-full ${
                isOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]'
              }`}
            />
            <span className="font-mono text-slate-300 hidden sm:inline">
              {isOnline ? 'MST Node Connected' : 'Local / Simulated'}
            </span>
          </div>
        </div>

      </div>
    </header>
  );
}

