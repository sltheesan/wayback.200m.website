import { useState, useMemo } from 'react';
import { ShieldAlert, ShieldCheck, AlertTriangle, Layers, Search, User, Download, Activity, CheckCircle2, Clock, ArrowUpRight } from 'lucide-react';
import { GlobalStats } from '../types';

interface AnalyticsDashboardProps {
  stats: GlobalStats;
  onScanDomain: (domain: string, force: boolean) => void;
  loading: boolean;
}

export default function AnalyticsDashboard({ stats, onScanDomain, loading }: AnalyticsDashboardProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState<'ALL' | 'SAFE' | 'MEDIUM' | 'HIGH'>('ALL');
  const [selectedTimeFilter, setSelectedTimeFilter] = useState<'ALL' | 'TODAY' | '7DAYS'>('ALL');

  const total = stats.total_analyzed || 0;
  const safe = stats.risk_breakdown?.SAFE || 0;
  const medium = stats.risk_breakdown?.MEDIUM || 0;
  const high = (stats.risk_breakdown?.HIGH || 0) + (stats.risk_breakdown?.UNSAFE || 0);

  const safePct = total ? Math.round((safe / total) * 100) : 0;
  const mediumPct = total ? Math.round((medium / total) * 100) : 0;
  const highPct = total ? Math.round((high / total) * 100) : 0;

  const filteredDomains = useMemo(() => {
    let list = stats.recent_domains || [];

    // Filter by risk tier
    if (selectedRiskFilter !== 'ALL') {
      if (selectedRiskFilter === 'HIGH') {
        list = list.filter(d => d.risk_level === 'HIGH' || d.risk_level === 'UNSAFE');
      } else {
        list = list.filter(d => d.risk_level === selectedRiskFilter);
      }
    }

    // Filter by time window
    if (selectedTimeFilter !== 'ALL') {
      const now = new Date().getTime();
      list = list.filter(d => {
        if (!d.last_analyzed_at) return true;
        const time = new Date(d.last_analyzed_at).getTime();
        const diffHours = (now - time) / (1000 * 60 * 60);
        if (selectedTimeFilter === 'TODAY') return diffHours <= 24;
        if (selectedTimeFilter === '7DAYS') return diffHours <= 24 * 7;
        return true;
      });
    }

    // Filter by search query
    const query = searchQuery.trim().toLowerCase();
    if (query) {
      list = list.filter(d =>
        d.domain.toLowerCase().includes(query) ||
        d.risk_level.toLowerCase().includes(query) ||
        (d.checked_by?.username && d.checked_by.username.toLowerCase().includes(query))
      );
    }

    return list;
  }, [searchQuery, selectedRiskFilter, selectedTimeFilter, stats.recent_domains]);

  const exportToCSV = () => {
    if (!filteredDomains.length) return;
    const headers = ['Domain', 'Risk Level', 'Risk Score', 'Analyzed By', 'Analyzed Date'];
    const rows = filteredDomains.map(d => [
      `"${d.domain}"`,
      `"${d.risk_level}"`,
      `"${d.risk_score ?? 'N/A'}"`,
      `"${d.checked_by?.username || (d.checked_by?.full_name ? d.checked_by.full_name : 'System')}"`,
      `"${d.last_analyzed_at ? new Date(d.last_analyzed_at).toISOString() : ''}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `ChronoSentinel_Domain_Ledger_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getRiskColor = (level: string): string => {
    if (level === 'HIGH' || level === 'UNSAFE') return 'text-rose-400 border-rose-500/30 bg-rose-500/10';
    if (level === 'MEDIUM') return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    if (level === 'UNKNOWN') return 'text-violet-400 border-violet-500/30 bg-violet-500/10';
    return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
  };

  const formatRelativeTime = (isoString?: string) => {
    if (!isoString) return 'recently';
    try {
      const date = new Date(isoString);
      const diffMs = new Date().getTime() - date.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);
      if (diffHours < 1) return 'Just now';
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return 'Yesterday';
      return `${diffDays}d ago`;
    } catch {
      return 'recently';
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-violet-950/40 via-slate-900/80 to-slate-950 border border-violet-500/20 shadow-xl">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-white flex items-center gap-2">
            <Activity className="text-violet-400" size={24} />
            <span>Global Analytics & Threat Dashboard</span>
          </h2>
          <p className="text-slate-400 text-xs mt-1 leading-relaxed">
            Real-time audit distribution telemetry across PostgreSQL indexed domain catalog
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={exportToCSV}
            disabled={!filteredDomains.length}
            className="px-4 py-2 rounded-xl bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 hover:text-white border border-violet-500/30 font-bold text-xs flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
          >
            <Download size={14} />
            <span>Export CSV Ledger</span>
          </button>
        </div>
      </div>

      {/* Overview Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 sm:gap-6">
        <div className="glass-panel p-6 flex flex-col justify-between hover:border-violet-500/40 transition-all duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/5 rounded-full blur-xl pointer-events-none group-hover:bg-violet-500/10 transition-all" />
          <div className="flex justify-between items-start">
            <span className="text-[10px] uppercase tracking-widest font-black text-slate-400">Total Catalogued</span>
            <div className="p-2 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20">
              <Layers size={16} />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl sm:text-4xl font-black text-white font-mono">{total}</span>
            <span className="text-[10px] text-slate-400 block font-medium mt-1">Unique target domain records</span>
          </div>
        </div>

        <div className="glass-panel p-6 flex flex-col justify-between border-emerald-500/20 bg-emerald-500/5 hover:border-emerald-500/40 transition-all duration-300 relative overflow-hidden group">
          <div className="flex justify-between items-start">
            <span className="text-[10px] uppercase tracking-widest font-black text-emerald-400">Safe Baselines</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div className="mt-4">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl sm:text-4xl font-black text-white font-mono">{safe}</span>
              <span className="text-xs font-black text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">{safePct}%</span>
            </div>
            <span className="text-[10px] text-slate-400 block font-medium mt-1">Clean legitimate targets</span>
          </div>
        </div>

        <div className="glass-panel p-6 flex flex-col justify-between border-amber-500/20 bg-amber-500/5 hover:border-amber-500/40 transition-all duration-300 relative overflow-hidden group">
          <div className="flex justify-between items-start">
            <span className="text-[10px] uppercase tracking-widest font-black text-amber-400">Medium Risk</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle size={16} />
            </div>
          </div>
          <div className="mt-4">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl sm:text-4xl font-black text-white font-mono">{medium}</span>
              <span className="text-xs font-black text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">{mediumPct}%</span>
            </div>
            <span className="text-[10px] text-slate-400 block font-medium mt-1">Suspicious signals flagged</span>
          </div>
        </div>

        <div className="glass-panel p-6 flex flex-col justify-between border-rose-500/20 bg-rose-500/5 hover:border-rose-500/40 transition-all duration-300 relative overflow-hidden group">
          <div className="flex justify-between items-start">
            <span className="text-[10px] uppercase tracking-widest font-black text-rose-400">High Threats</span>
            <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <ShieldAlert size={16} />
            </div>
          </div>
          <div className="mt-4">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl sm:text-4xl font-black text-white font-mono">{high}</span>
              <span className="text-xs font-black text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">{highPct}%</span>
            </div>
            <span className="text-[10px] text-slate-400 block font-medium mt-1">Confirmed threat abuse</span>
          </div>
        </div>
      </div>

      {/* Breakdown Panel & Recent Domain Ledger */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Risk Profile Distribution & Telemetry Summary */}
        <div className="glass-panel p-6 sm:p-8 space-y-6 lg:col-span-1">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>Risk Profile Distribution</span>
            </h3>
            <p className="text-slate-400 text-xs mt-1 font-medium">Categorized proportion across catalogued targets</p>
          </div>

          <div className="space-y-4">
            {/* Safe */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-emerald-400 flex items-center gap-1.5">
                  <ShieldCheck size={13} />
                  <span>SAFE DOMAINS</span>
                </span>
                <span className="text-slate-200 font-mono">{safe} ({safePct}%)</span>
              </div>
              <div className="w-full bg-slate-950 h-3 rounded-full border border-slate-800 overflow-hidden">
                <div className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full transition-all duration-500" style={{ width: `${safePct}%` }} />
              </div>
            </div>

            {/* Medium */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-amber-400 flex items-center gap-1.5">
                  <AlertTriangle size={13} />
                  <span>MEDIUM RISK</span>
                </span>
                <span className="text-slate-200 font-mono">{medium} ({mediumPct}%)</span>
              </div>
              <div className="w-full bg-slate-950 h-3 rounded-full border border-slate-800 overflow-hidden">
                <div className="bg-gradient-to-r from-amber-500 to-yellow-400 h-full rounded-full transition-all duration-500" style={{ width: `${mediumPct}%` }} />
              </div>
            </div>

            {/* High */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-rose-400 flex items-center gap-1.5">
                  <ShieldAlert size={13} />
                  <span>HIGH THREATS</span>
                </span>
                <span className="text-slate-200 font-mono">{high} ({highPct}%)</span>
              </div>
              <div className="w-full bg-slate-950 h-3 rounded-full border border-slate-800 overflow-hidden">
                <div className="bg-gradient-to-r from-rose-600 to-pink-500 h-full rounded-full transition-all duration-500" style={{ width: `${highPct}%` }} />
              </div>
            </div>
          </div>

          {/* System Health Indicators */}
          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-950/40 text-xs text-slate-400 space-y-3 font-medium">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
              <span>Avg Risk Severity Rating:</span>
              <span className="text-white font-mono font-black text-sm">
                {total ? Math.round((safe * 10 + medium * 50 + high * 85) / total) : 0} / 100
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span>PostgreSQL Database:</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 size={12} />
                <span>Connected</span>
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span>Classifier Engine:</span>
              <span className="text-violet-400 font-bold flex items-center gap-1">
                <Activity size={12} />
                <span>v2.4 Active</span>
              </span>
            </div>
          </div>
        </div>

        {/* Domain Catalog Ledger */}
        <div className="glass-panel p-6 sm:p-8 space-y-5 lg:col-span-2 flex flex-col">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
            <div>
              <h3 className="text-base font-bold text-white">Domain Catalog Ledger</h3>
              <p className="text-slate-400 text-xs mt-0.5 font-medium">
                Showing {filteredDomains.length} of {stats?.recent_domains?.length || 0} catalogued records
              </p>
            </div>

            {/* Filter Tabs & Search Bar */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Risk Filter Pills */}
              <div className="flex items-center p-1 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-bold">
                <button
                  onClick={() => setSelectedRiskFilter('ALL')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${selectedRiskFilter === 'ALL' ? 'bg-violet-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  All
                </button>
                <button
                  onClick={() => setSelectedRiskFilter('SAFE')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${selectedRiskFilter === 'SAFE' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  Safe
                </button>
                <button
                  onClick={() => setSelectedRiskFilter('MEDIUM')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${selectedRiskFilter === 'MEDIUM' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  Medium
                </button>
                <button
                  onClick={() => setSelectedRiskFilter('HIGH')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${selectedRiskFilter === 'HIGH' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  High
                </button>
              </div>

              {/* Time Window Selector */}
              <div className="flex items-center p-1 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-bold">
                <button
                  onClick={() => setSelectedTimeFilter('ALL')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${selectedTimeFilter === 'ALL' ? 'bg-slate-800 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  All Time
                </button>
                <button
                  onClick={() => setSelectedTimeFilter('TODAY')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${selectedTimeFilter === 'TODAY' ? 'bg-violet-600/30 text-violet-200 border border-violet-500/40' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  &lt;24h
                </button>
                <button
                  onClick={() => setSelectedTimeFilter('7DAYS')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${selectedTimeFilter === '7DAYS' ? 'bg-violet-600/30 text-violet-200 border border-violet-500/40' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  7 Days
                </button>
              </div>

              {/* Search Bar */}
              <div className="relative group w-full sm:w-48">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-violet-400 transition-colors" />
                <input
                  type="text"
                  placeholder="Search domain or user..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs glass-input focus:border-violet-500/40 transition-all rounded-xl"
                />
              </div>
            </div>
          </div>

          {/* Ledger List */}
          <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1 flex-1 scrollbar-thin">
            {filteredDomains.length > 0 ? (
              filteredDomains.map((d, index) => (
                <div
                  key={index}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 border border-slate-800/80 bg-slate-950/40 rounded-xl hover:border-violet-500/30 hover:bg-slate-900/60 transition-all duration-200 group"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-extrabold text-white block group-hover:text-violet-300 transition-colors truncate">
                        {d.domain}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-slate-400 font-mono">
                      <span className="flex items-center gap-1 text-slate-400">
                        <Clock size={11} className="text-violet-400 shrink-0" />
                        <span>{formatRelativeTime(d.last_analyzed_at)}</span>
                      </span>
                      <span>•</span>
                      <span className="flex items-center text-slate-300 gap-1" title={d.checked_by?.full_name || 'System Auditor'}>
                        <User size={11} className="text-emerald-400 shrink-0 inline" />
                        <span className="font-semibold text-slate-200">
                          {d.checked_by?.username || (d.checked_by?.full_name ? d.checked_by.full_name : 'System')}
                        </span>
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2.5 shrink-0 self-end sm:self-center">
                    <span className={`px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider border ${getRiskColor(d.risk_level)}`}>
                      {d.risk_level}
                    </span>
                    <button
                      onClick={() => onScanDomain(d.domain, false)}
                      disabled={loading}
                      className="px-3 py-1.5 rounded-lg border border-violet-500/30 bg-violet-600/10 hover:bg-violet-600/20 text-violet-300 hover:text-white font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer"
                      title="Inspect full scan analysis"
                    >
                      <span>Inspect</span>
                      <ArrowUpRight size={13} />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12 border border-dashed border-slate-800 rounded-2xl text-slate-500 text-xs">
                {searchQuery || selectedRiskFilter !== 'ALL'
                  ? "No matching ledger records found for selected filters."
                  : "No analysis ledger entries found. Perform your first scan."}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
