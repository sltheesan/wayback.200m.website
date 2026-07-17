import { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from 'recharts';
import { ExternalLink, Calendar, ChevronDown, ChevronUp } from 'lucide-react';
import { Snapshot } from '../types';

interface SnapshotTimelineProps {
  snapshots: Snapshot[];
}

interface ChartDataPoint {
  name: string;
  timestamp: string;
  score: number;
  url: string;
  status: number | null;
  flagsCount: number;
  fullDate: string;
}

const getScoreColor = (score: number, category?: string | null): string => {
  if (!category || category === 'safe') return 'text-emerald-400';
  if (score > 70) return 'text-rose-400';
  return 'text-amber-400';
};

const getScoreBg = (score: number, category?: string | null): string => {
  if (!category || category === 'safe') return 'bg-emerald-500/10 border-emerald-500/20';
  if (score > 70) return 'bg-rose-500/10 border-rose-500/20';
  return 'bg-amber-500/10 border-amber-500/20';
};

const getCardStyles = (score: number, category: string | null | undefined, isActive: boolean): string => {
  if (!category || category === 'safe') {
    return isActive
      ? 'border-l-4 border-l-emerald-500 border-emerald-500/50 bg-gradient-to-r from-emerald-950/20 to-slate-900/10 shadow-[0_0_15px_rgba(16,185,129,0.25)] scale-[1.01]'
      : 'border-l-4 border-l-emerald-500/60 border-emerald-950/40 bg-emerald-950/5 hover:border-emerald-500/40 hover:bg-emerald-950/10';
  }
  if (score > 70) {
    return isActive
      ? 'border-l-4 border-l-rose-500 border-rose-500/50 bg-gradient-to-r from-rose-950/20 to-slate-900/10 shadow-[0_0_15px_rgba(244,63,94,0.25)] scale-[1.01]'
      : 'border-l-4 border-l-rose-500/60 border-rose-950/40 bg-rose-950/5 hover:border-rose-500/40 hover:bg-rose-950/10';
  }
  return isActive
    ? 'border-l-4 border-l-amber-500 border-amber-500/50 bg-gradient-to-r from-amber-950/20 to-slate-900/10 shadow-[0_0_15px_rgba(245,158,11,0.25)] scale-[1.01]'
    : 'border-l-4 border-l-amber-500/60 border-amber-950/40 bg-amber-950/5 hover:border-amber-500/40 hover:bg-amber-950/10';
};

const getCategoryTagStyle = (score: number, category?: string | null): string => {
  if (!category || category === 'safe') return 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20';
  if (score > 70) return 'bg-rose-500/10 text-rose-300 border border-rose-500/20';
  return 'bg-amber-500/10 text-amber-300 border border-amber-500/20';
};

interface SnapshotCardProps {
  s: Snapshot;
  onSelect?: (s: Snapshot) => void;
  isActive: boolean;
}

const CATEGORY_ICONS: Record<string, string> = {
  gambling: '🎰',
  adult: '🔞',
  phishing_scam: '🎣',
  malware_hacking: '💀',
  illegal_pharmaceuticals: '💊',
  safe: '✅',
};

const getPanelColors = (score: number, category?: string | null) => {
  if (!category || category === 'safe') return 'border-emerald-500/20 bg-emerald-500/5 text-emerald-300';
  if (score >= 70) return 'border-rose-500/20 bg-rose-500/5 text-rose-300';
  return 'border-amber-500/20 bg-amber-500/5 text-amber-300';
};

const getPulseColor = (score: number, category?: string | null) => {
  if (!category || category === 'safe') return 'bg-emerald-500';
  if (score >= 70) return 'bg-rose-500';
  return 'bg-amber-500';
};

const highlightKeyword = (text: string | null | undefined, keyword: string) => {
  if (!text) return null;
  if (!keyword) return <span>{text}</span>;
  
  const escapedKeyword = keyword.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
  const regex = new RegExp(`(${escapedKeyword})`, 'gi');
  const parts = text.split(regex);
  
  return (
    <span>
      {parts.map((part, i) => 
        regex.test(part) ? (
          <mark key={i} className="bg-amber-500/30 text-amber-300 px-1 py-0.5 rounded font-extrabold font-mono border border-amber-500/20">
            {part}
          </mark>
        ) : (
          part
        )
      )}
    </span>
  );
};

const formatLocationLabel = (rawElement: string | null | undefined): string => {
  if (!rawElement) return "Page Contents";
  
  const clean = rawElement.toLowerCase().trim();
  
  if (clean.includes("meta")) {
    const nameMatch = clean.match(/name="([^"]+)"/) || clean.match(/property="([^"]+)"/);
    if (nameMatch && nameMatch[1]) {
      return `HTML Meta Tag (${nameMatch[1]})`;
    }
    return "HTML Meta Tag (Head Metadata)";
  }
  
  if (clean === "<title>") {
    return "HTML Document Title (<title>)";
  }
  if (clean === "<a>") {
    return "HTML Anchor / Link (<a>)";
  }
  if (clean.match(/^<h[1-6]>$/)) {
    return `HTML Heading (${clean.toUpperCase()})`;
  }
  if (clean === "<p>") {
    return "HTML Body Paragraph (<p>)";
  }
  if (clean === "<div>") {
    return "HTML Content Div (<div>)";
  }
  if (clean === "<span>") {
    return "HTML Inline Text (<span>)";
  }
  if (clean === "<li>") {
    return "HTML List Item (<li>)";
  }
  
  return `HTML Element (${rawElement})`;
};

function SnapshotCard({ s, onSelect, isActive }: SnapshotCardProps) {
  const [expanded, setExpanded] = useState(false);

  const year = s.timestamp.substring(0, 4);
  const month = s.timestamp.substring(4, 6);
  const day = s.timestamp.substring(6, 8);
  const dateStr = new Date(`${year}-${month}-${day}`).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
  
  const directWaybackUrl = `https://web.archive.org/web/${s.timestamp}/${s.original_url}`;
  const apiBase = (import.meta.env.VITE_API_URL as string) || '/api/v1';
  const proxyUrl = `${apiBase}/domains/proxy-snapshot?timestamp=${s.timestamp}&url=${encodeURIComponent(s.original_url)}`;

  const getLanguageLabel = (lang: string | null) => {
    if (!lang) return '🇺🇸 EN';
    const l = lang.toLowerCase();
    if (l === 'id') return '🇮🇩 ID';
    if (l === 'nl') return '🇳🇱 NL';
    if (l === 'de') return '🇩🇪 DE';
    if (l === 'fr') return '🇫🇷 FR';
    if (l === 'es') return '🇪🇸 ES';
    return `🌐 ${l.toUpperCase()}`;
  };

  const catIcon = CATEGORY_ICONS[s.content_category || 'safe'] || '❓';
  const catLabel = (s.content_category || 'safe').replace(/_/g, ' ').toUpperCase();

  return (
    <div
      onClick={() => onSelect?.(s)}
      className={`border rounded-xl overflow-hidden transition-all duration-200 cursor-pointer ${getCardStyles(s.risk_score, s.content_category, isActive)}`}
    >
      {/* Card Header (clickable) */}
      <div
        className="flex flex-wrap items-center justify-between gap-2 p-3 sm:p-3.5 select-none"
      >
        <div className="flex items-center space-x-3">
          <div className={`p-2.5 rounded-lg border text-center min-w-[50px] ${getScoreBg(s.risk_score, s.content_category)}`}>
            <span className={`text-sm font-extrabold block ${getScoreColor(s.risk_score, s.content_category)}`}>
              {s.risk_score}
            </span>
            <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest leading-none">Score</span>
          </div>
          <div>
            <div className="flex items-center space-x-2 text-xs font-semibold text-white">
              <Calendar size={13} className="text-slate-500" />
              <span>{dateStr}</span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${getCategoryTagStyle(s.risk_score, s.content_category)}`}>
                {catIcon} {catLabel}
              </span>
            </div>
            <div className="flex items-center space-x-1.5 text-[10px] text-slate-400 font-mono mt-0.5">
              <span>Status: {s.status_code ?? 200}</span>
              <span>•</span>
              <span>Lang: <span className="text-violet-400 font-bold">{getLanguageLabel(s.detected_language)}</span></span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2" onClick={(e) => e.stopPropagation()}>
          <a
            href={proxyUrl}
            target="_blank"
            rel="noreferrer"
            className="p-1.5 text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 rounded-md bg-slate-900/40 transition-colors"
            title="Open in Proxy Snapshot View (Works offline/locally)"
          >
            <ExternalLink size={14} />
          </a>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1.5 text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 rounded-md bg-slate-900/40 transition-colors"
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {/* Accordion content */}
      {expanded && (
        <div className="bg-slate-950/50 border-t border-slate-900/60 p-4 space-y-3 text-xs" onClick={e => e.stopPropagation()}>
          {s.timestamp && s.original_url && (
            <div className={`space-y-2 rounded-lg border p-3 ${getPanelColors(s.risk_score, s.content_category)}`}>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[10px] font-extrabold uppercase tracking-widest flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full animate-pulse ${getPulseColor(s.risk_score, s.content_category)}`} />
                  Visual Evidence Preview (Proxied)
                </span>
                <div className="flex items-center space-x-2">
                  <a
                    href={proxyUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] font-bold hover:text-white font-semibold"
                  >
                    Open Proxied <ExternalLink size={11} />
                  </a>
                  <span className="text-slate-700">|</span>
                  <a
                    href={directWaybackUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-400 hover:text-white"
                    title="Requires VPN if your network blocks archive.org"
                  >
                    Open Direct <ExternalLink size={11} />
                  </a>
                </div>
              </div>
              <div className="h-48 overflow-hidden rounded-md border border-slate-800 bg-slate-950">
                <iframe
                  src={proxyUrl}
                  title={`Evidence preview for ${s.original_url}`}
                  className="h-full w-full bg-white"
                  loading="lazy"
                  referrerPolicy="no-referrer"
                />
              </div>
            </div>
          )}

          {s.content_summary && (
            <div className="p-2 border border-slate-900 bg-slate-950/80 rounded-lg text-[10px] text-slate-300 font-medium">
              ℹ️ {s.content_summary}
            </div>
          )}

          <div className="flex justify-between items-center text-[10px] uppercase tracking-wider font-extrabold text-slate-500">
            <span>Snapshot Scan Log</span>
            <span>{s.flags.length} Flagged Terms</span>
          </div>

          {s.flags.length > 0 ? (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {s.flags.map((f, idx) => (
                <div key={idx} className="flex flex-col p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-extrabold text-white font-mono text-[12px] bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                          "{f.keyword}"
                        </span>
                        <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                          {f.category.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </div>
                    <div className="text-right flex items-center space-x-2">
                      <span className="text-[10px] text-slate-500 font-medium">
                        {f.match_count} match{f.match_count > 1 ? 'es' : ''}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/25 font-bold font-mono text-[10px]">
                        +{f.weight} pts
                      </span>
                    </div>
                  </div>
                  
                  {/* Expanded evidence details */}
                  {(f.element || f.snippet) && (
                    <div className="pt-1.5 border-t border-slate-850 space-y-1">
                      {f.element && (
                        <div className="flex items-center space-x-1 text-[9px] text-slate-500 font-bold uppercase tracking-wider">
                          <span>📍 Location:</span>
                          <span className="text-violet-400 font-semibold bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 font-mono text-[10px]">
                            {formatLocationLabel(f.element)}
                          </span>
                        </div>
                      )}
                      {f.snippet && (
                        <div className="p-2 bg-slate-950/60 rounded-md border border-slate-900 font-mono text-[10px] text-slate-400 leading-relaxed overflow-x-auto whitespace-pre-wrap break-all max-w-full">
                          <span className="text-slate-600 mr-1 select-none">Snippet:</span>
                          {highlightKeyword(f.snippet, f.keyword)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-4 border border-dashed border-slate-900 rounded-lg text-slate-500 text-xs">
              No risk flags triggered. Content matches clean baseline signatures.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface SnapshotTimelineProps {
  snapshots: Snapshot[];
  activeSnapshot?: Snapshot | null;
  onSelectSnapshot?: (s: Snapshot) => void;
}

export default function SnapshotTimeline({ snapshots, activeSnapshot, onSelectSnapshot }: SnapshotTimelineProps) {
  if (!snapshots || snapshots.length === 0) return null;

  const chartData: ChartDataPoint[] = snapshots.map((s) => {
    const year = s.timestamp.substring(0, 4);
    const month = s.timestamp.substring(4, 6);
    const day = s.timestamp.substring(6, 8);

    return {
      name: `${year}-${month}-${day}`,
      timestamp: s.timestamp,
      score: s.risk_score,
      url: s.original_url,
      status: s.status_code,
      flagsCount: s.flags.length,
      fullDate: new Date(`${year}-${month}-${day}`).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
      }),
    };
  });

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: ChartDataPoint }> }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-900 border border-slate-700/80 p-3 rounded-lg shadow-xl text-xs max-w-xs space-y-1.5 backdrop-blur-md">
          <p className="font-bold text-slate-200">{data.fullDate}</p>
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Risk Score:</span>
            <span className={`font-extrabold ${getScoreColor(data.score, undefined)}`}>{data.score}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Status:</span>
            <span className="text-slate-200 font-mono">{data.status ?? 200}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Risk Flags:</span>
            <span className="text-slate-200">{data.flagsCount} triggered</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-panel p-6 sm:p-8 space-y-6">
      <div>
        <h3 className="text-lg font-bold mb-1">Historical Snapshot Timeline</h3>
        <p className="text-slate-400 text-sm">
          Risk rating trend calculated from content scans of Wayback captures spanning{' '}
          {chartData[0].name} to {chartData[chartData.length - 1].name}. Click on a card below to load its AI Content Scan details.
        </p>
      </div>

      {/* Recharts Area Chart */}
      <div className="h-64 min-h-64 w-full min-w-0 overflow-hidden">
        <ResponsiveContainer width="100%" height={256} minWidth={1} minHeight={1}>
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="scoreColor" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#7c3aed" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.5} />
            <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="score"
              stroke="#8b5cf6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#scoreColor)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Snapshot Cards List */}
      <div className="space-y-3.5">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Analyzed Snapshot Details
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 max-h-[340px] overflow-y-auto pr-1">
          {snapshots.map((s, index) => (
            <SnapshotCard
              key={index}
              s={s}
              onSelect={onSelectSnapshot}
              isActive={activeSnapshot?.timestamp === s.timestamp}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
