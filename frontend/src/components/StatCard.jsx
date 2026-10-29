import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'cyan' }) {
  const colorStyles = {
    cyan: 'from-cyan-500/20 to-transparent text-cyan-400 border-cyan-500/30',
    emerald: 'from-emerald-500/20 to-transparent text-emerald-400 border-emerald-500/30',
    amber: 'from-amber-500/20 to-transparent text-amber-400 border-amber-500/30',
    rose: 'from-rose-500/20 to-transparent text-rose-400 border-rose-500/30',
    indigo: 'from-indigo-500/20 to-transparent text-indigo-400 border-indigo-500/30',
  }[color] || 'from-cyan-500/20 to-transparent text-cyan-400 border-cyan-500/30';

  return (
    <div className="glass-panel rounded-xl p-5 relative overflow-hidden transition-all duration-300 hover:border-slate-600/80 hover:translate-y-[-2px]">
      <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${colorStyles} rounded-full blur-2xl pointer-events-none opacity-40`} />
      
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {Icon && (
          <div className="p-2 rounded-lg bg-navy-800/80 border border-slate-700/60">
            <Icon className="w-5 h-5 text-slate-300" />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold font-mono tracking-tight text-white">
          {value}
        </span>
      </div>

      {subtitle && (
        <p className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
          {subtitle}
        </p>
      )}
    </div>
  );
}

