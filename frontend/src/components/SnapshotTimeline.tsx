import { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from 'recharts';
import { ExternalLink, Calendar, Shield, AlertTriangle, CheckCircle, Layers, Hash, Eye, Flag } from 'lucide-react';
import { Snapshot } from '../types';

interface SnapshotTimelineProps {
  snapshots: Snapshot[];
  activeSnapshot?: Snapshot | null;
  onSelectSnapshot?: (s: Snapshot) => void;
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

/* ─── Colour helpers ──────────────────────────────────────────── */
const getRiskPalette = (score: number, category?: string | null) => {
  const isSafe = !category || category === 'safe';
  if (isSafe && score < 70) {
    return { accent: '#10b981', dim: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.25)', text: '#10b981', glow: '0 0 16px rgba(16,185,129,0.2)' };
  }
  // For unsafe categories (gambling, adult, gaming, etc.) or high scores, show red (high risk color)
  return { accent: '#f43f5e', dim: 'rgba(244,63,94,0.12)', border: 'rgba(244,63,94,0.25)', text: '#f43f5e', glow: '0 0 16px rgba(244,63,94,0.2)' };
};

const CATEGORY_ICONS: Record<string, string> = {
  gambling: '🎰', adult: '🔞', phishing_scam: '🎣',
  malware_hacking: '💀', illegal_pharmaceuticals: '💊', safe: '✅',
  gaming: '🎮',
};

const formatDate = (timestamp: string) =>
  new Date(`${timestamp.slice(0,4)}-${timestamp.slice(4,6)}-${timestamp.slice(6,8)}`).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });

const formatLocationLabel = (rawElement: string | null | undefined): string => {
  if (!rawElement) return 'Page Contents';
  const clean = rawElement.toLowerCase().trim();
  if (clean.includes('meta')) {
    const m = clean.match(/name="([^"]+)"/) || clean.match(/property="([^"]+)"/);
    if (m?.[1]) return `HTML Meta Tag (${m[1]})`;
    return 'HTML Meta Tag (Head Metadata)';
  }
  if (clean === '<title>') return 'HTML Document Title (<title>)';
  if (clean === '<a>') return 'HTML Anchor / Link (<a>)';
  if (clean.match(/^<h[1-6]>$/)) return `HTML Heading (${clean.toUpperCase()})`;
  if (clean === '<p>') return 'HTML Body Paragraph (<p>)';
  if (clean === '<div>') return 'HTML Content Div (<div>)';
  if (clean === '<span>') return 'HTML Inline Text (<span>)';
  if (clean === '<li>') return 'HTML List Item (<li>)';
  return `HTML Element (${rawElement})`;
};

const highlightKeyword = (text: string | null | undefined, keyword: string) => {
  if (!text) return null;
  if (!keyword) return <span>{text}</span>;
  const escaped = keyword.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);
  return (
    <span>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} style={{ background: 'rgba(245,158,11,0.3)', color: '#fcd34d', padding: '0 3px', borderRadius: 3, fontWeight: 700, fontFamily: 'monospace', border: '1px solid rgba(245,158,11,0.25)' }}>
            {part}
          </mark>
        ) : part
      )}
    </span>
  );
};

/* ─── Right panel: full snapshot detail ───────────────────────── */
function SnapshotDetailPanel({ s }: { s: Snapshot }) {
  const pal = getRiskPalette(s.risk_score, s.content_category);
  const apiBase = (import.meta.env.VITE_API_URL as string) || '/api/v1';
  const proxyUrl = `${apiBase}/domains/proxy-snapshot?timestamp=${s.timestamp}&url=${encodeURIComponent(s.original_url)}`;
  const directUrl = `https://web.archive.org/web/${s.timestamp}/${s.original_url}`;
  const catLabel = (s.content_category || 'safe').replace(/_/g, ' ').toUpperCase();
  const catIcon = CATEGORY_ICONS[s.content_category || 'safe'] || '❓';

  const getLanguageLabel = (lang: string | null) => {
    if (!lang) return '🇺🇸 EN';
    const l = lang.toLowerCase();
    if (l === 'id') return '🇮🇩 ID'; if (l === 'nl') return '🇳🇱 NL';
    if (l === 'de') return '🇩🇪 DE'; if (l === 'fr') return '🇫🇷 FR';
    if (l === 'es') return '🇪🇸 ES';
    return `🌐 ${l.toUpperCase()}`;
  };

  return (
    <div style={{
      background: 'rgba(10,14,26,0.85)',
      border: `1px solid ${pal.border}`,
      borderRadius: 18,
      overflow: 'hidden',
      boxShadow: pal.glow,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Panel Header */}
      <div style={{
        padding: '18px 22px 14px',
        background: `linear-gradient(135deg, ${pal.dim} 0%, rgba(10,14,26,0) 60%)`,
        borderBottom: `1px solid ${pal.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Risk score badge */}
          <div style={{
            width: 56, height: 56, borderRadius: 14,
            background: pal.dim, border: `2px solid ${pal.border}`,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <span style={{ color: pal.accent, fontWeight: 800, fontSize: 20, lineHeight: 1 }}>{s.risk_score}</span>
            <span style={{ color: 'rgba(148,163,184,0.7)', fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginTop: 2 }}>score</span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <Calendar size={12} color="#64748b" />
              <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 14 }}>{formatDate(s.timestamp)}</span>
              <span style={{
                padding: '2px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700,
                background: pal.dim, border: `1px solid ${pal.border}`, color: pal.text,
              }}>{catIcon} {catLabel}</span>
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 5, fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>
              <span>HTTP <span style={{ color: '#a5b4fc', fontWeight: 700 }}>{s.status_code ?? 200}</span></span>
              <span>·</span>
              <span>Lang <span style={{ color: '#c4b5fd', fontWeight: 700 }}>{getLanguageLabel(s.detected_language)}</span></span>
              <span>·</span>
              <span><span style={{ color: '#f87171', fontWeight: 700 }}>{s.flags.length}</span> flags</span>
            </div>
          </div>
        </div>
        {/* Quick links */}
        <div style={{ display: 'flex', gap: 8 }}>
          <a href={proxyUrl} target="_blank" rel="noreferrer" style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px',
            borderRadius: 8, background: pal.dim, border: `1px solid ${pal.border}`,
            color: pal.text, fontSize: 11, fontWeight: 700, textDecoration: 'none',
          }}>
            <Eye size={12} /> Proxy View
          </a>
          <a href={directUrl} target="_blank" rel="noreferrer" style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px',
            borderRadius: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            color: '#94a3b8', fontSize: 11, fontWeight: 700, textDecoration: 'none',
          }}>
            <ExternalLink size={12} /> Wayback
          </a>
        </div>
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Preview iframe */}
        <div style={{
          borderRadius: 12, border: `1px solid ${pal.border}`,
          background: 'rgba(0,0,0,0.3)', overflow: 'hidden',
        }}>
          <div style={{
            padding: '8px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            borderBottom: `1px solid rgba(255,255,255,0.04)`, background: 'rgba(255,255,255,0.02)',
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: pal.text }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: pal.accent, display: 'inline-block', animation: 'pulse-dot 2s ease-in-out infinite' }} />
              Visual Evidence Preview
            </span>
          </div>
          <div style={{ height: 200, background: '#fff' }}>
            <iframe
              src={proxyUrl}
              title={`Preview: ${s.original_url}`}
              style={{ width: '100%', height: '100%', border: 'none' }}
              loading="lazy"
              referrerPolicy="no-referrer"
            />
          </div>
        </div>

        {/* Content summary */}
        {s.content_summary && (
          <div style={{
            padding: '10px 14px', borderRadius: 10,
            background: 'rgba(148,163,184,0.04)', border: '1px solid rgba(148,163,184,0.1)',
            fontSize: 12, color: '#94a3b8', lineHeight: 1.6,
          }}>
            <span style={{ color: '#64748b', fontWeight: 700, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 4 }}>ℹ️ Content Summary</span>
            {s.content_summary}
          </div>
        )}

        {/* Flags section */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#64748b' }}>
              <Flag size={11} /> Snapshot Scan Log
            </span>
            <span style={{
              padding: '2px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700,
              background: s.flags.length > 0 ? 'rgba(244,63,94,0.12)' : 'rgba(16,185,129,0.12)',
              color: s.flags.length > 0 ? '#f87171' : '#34d399',
              border: `1px solid ${s.flags.length > 0 ? 'rgba(244,63,94,0.25)' : 'rgba(16,185,129,0.25)'}`,
            }}>
              {s.flags.length} Flagged Terms
            </span>
          </div>

          {s.flags.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {s.flags.map((f, idx) => (
                <div key={idx} style={{
                  padding: '12px 14px', borderRadius: 10,
                  background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(255,255,255,0.06)',
                  display: 'flex', flexDirection: 'column', gap: 8,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <code style={{
                        fontFamily: 'monospace', fontSize: 12, fontWeight: 700, color: '#f1f5f9',
                        background: 'rgba(0,0,0,0.4)', padding: '2px 8px', borderRadius: 5,
                        border: '1px solid rgba(255,255,255,0.08)',
                      }}>"{f.keyword}"</code>
                      <span style={{
                        fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
                        background: 'rgba(0,0,0,0.3)', color: '#94a3b8',
                        padding: '2px 6px', borderRadius: 4, border: '1px solid rgba(255,255,255,0.06)',
                      }}>{f.category.replace(/_/g, ' ')}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, color: '#64748b' }}>{f.match_count} match{f.match_count > 1 ? 'es' : ''}</span>
                      <span style={{
                        padding: '2px 7px', borderRadius: 5, fontSize: 10, fontWeight: 700, fontFamily: 'monospace',
                        background: 'rgba(244,63,94,0.12)', color: '#f87171', border: '1px solid rgba(244,63,94,0.25)',
                      }}>+{f.weight} pts</span>
                    </div>
                  </div>
                  {(f.element || f.snippet) && (
                    <div style={{ paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {f.element && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10 }}>
                          <span style={{ color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>📍 Location:</span>
                          <span style={{
                            color: '#a78bfa', fontWeight: 600, fontFamily: 'monospace',
                            background: 'rgba(0,0,0,0.3)', padding: '1px 7px', borderRadius: 4,
                            border: '1px solid rgba(139,92,246,0.2)', fontSize: 10,
                          }}>{formatLocationLabel(f.element)}</span>
                        </div>
                      )}
                      {f.snippet && (
                        <div style={{
                          padding: '8px 10px', background: 'rgba(0,0,0,0.35)', borderRadius: 7,
                          border: '1px solid rgba(255,255,255,0.05)', fontFamily: 'monospace',
                          fontSize: 10, color: '#94a3b8', lineHeight: 1.6, overflowX: 'auto',
                          whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                        }}>
                          <span style={{ color: '#475569', marginRight: 6, userSelect: 'none' }}>Snippet:</span>
                          {highlightKeyword(f.snippet, f.keyword)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              padding: '28px 20px', borderRadius: 12,
              border: '1px dashed rgba(16,185,129,0.25)', background: 'rgba(16,185,129,0.04)',
              gap: 8,
            }}>
              <CheckCircle size={22} color="#10b981" />
              <span style={{ fontSize: 12, color: '#34d399', fontWeight: 600 }}>No risk flags triggered</span>
              <span style={{ fontSize: 11, color: '#64748b' }}>Content matches clean baseline signatures.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Left panel: compact tab for one snapshot ────────────────── */
interface SnapshotTabProps {
  s: Snapshot;
  index: number;
  isSelected: boolean;
  onSelect: (s: Snapshot) => void;
}

function SnapshotTab({ s, index, isSelected, onSelect }: SnapshotTabProps) {
  const isUnsafe = (s.content_category && s.content_category !== 'safe') || s.risk_score >= 70;
  const pal = getRiskPalette(s.risk_score, s.content_category);
  const catIcon = CATEGORY_ICONS[s.content_category || 'safe'] || '❓';
  const catLabel = (s.content_category || 'safe').replace(/_/g, ' ');
  const dateStr = formatDate(s.timestamp);
  const rawDate = `${s.timestamp.slice(0, 4)}/${s.timestamp.slice(4, 6)}/${s.timestamp.slice(6, 8)}`;

  // SVG Circular progress config
  const R = 30;
  const SW = 4;
  const circ = 2 * Math.PI * R;
  const offset = circ - (s.risk_score / 100) * circ;

  const getCatStyle = (cat: string | null) => {
    switch (cat || 'safe') {
      case 'adult':
        return { bg: 'rgba(244,63,94,0.15)', border: 'rgba(244,63,94,0.35)', color: '#f87171' };
      case 'gambling':
        return { bg: 'rgba(245,158,11,0.15)', border: 'rgba(245,158,11,0.35)', color: '#fbbf24' };
      case 'gaming':
        return { bg: 'rgba(59,130,246,0.15)', border: 'rgba(59,130,246,0.35)', color: '#60a5fa' };
      case 'phishing_scam':
      case 'malware_hacking':
      case 'illegal_pharmaceuticals':
        return { bg: 'rgba(167,139,250,0.15)', border: 'rgba(167,139,250,0.35)', color: '#c084fc' };
      default:
        return { bg: 'rgba(16,185,129,0.15)', border: 'rgba(16,185,129,0.35)', color: '#34d399' };
    }
  };

  const catStyle = getCatStyle(s.content_category);

  const cardBg = isSelected
    ? `linear-gradient(145deg, rgba(17,24,39,0.98) 0%, rgba(10,14,26,0.95) 100%)`
    : `linear-gradient(145deg, rgba(15,23,42,0.75) 0%, rgba(10,14,26,0.6) 100%)`;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(s)}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') onSelect(s); }}
      style={{
        width: '100%',
        padding: 0,
        borderRadius: 18,
        background: cardBg,
        border: `2px solid ${isSelected ? pal.accent + 'cc' : 'rgba(255,255,255,0.08)'}`,
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'all 0.28s cubic-bezier(0.4, 0, 0.2, 1)',
        boxShadow: isSelected
          ? `${pal.glow}, 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1)`
          : '0 4px 16px rgba(0,0,0,0.35)',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflow: 'hidden',
        transform: isSelected ? 'translateY(-4px) scale(1.01)' : 'translateY(0) scale(1)',
        userSelect: 'none',
        outline: 'none',
      }}
      onMouseEnter={e => {
        if (!isSelected) {
          const el = e.currentTarget as HTMLDivElement;
          el.style.background = `linear-gradient(145deg, rgba(20,28,48,0.95) 0%, rgba(15,22,40,0.9) 100%)`;
          el.style.borderColor = `${pal.accent}60`;
          el.style.transform = 'translateY(-3px) scale(1.005)';
          el.style.boxShadow = `0 12px 32px rgba(0,0,0,0.55), 0 0 0 1px ${pal.accent}20`;
        }
      }}
      onMouseLeave={e => {
        if (!isSelected) {
          const el = e.currentTarget as HTMLDivElement;
          el.style.background = cardBg;
          el.style.borderColor = 'rgba(255,255,255,0.08)';
          el.style.transform = 'translateY(0) scale(1)';
          el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.35)';
        }
      }}
    >
      {/* ── SELECTED ACCENT LINE (left edge) ─────────────────────── */}
      {isSelected && (
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0, width: 4,
          background: `linear-gradient(180deg, ${pal.accent}, ${pal.accent}80)`,
          boxShadow: `0 0 12px ${pal.accent}`,
          borderRadius: '18px 0 0 18px',
        }} />
      )}

      {/* ── HEADER ─────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px 12px 18px',
        background: isUnsafe
          ? 'linear-gradient(90deg, rgba(244,63,94,0.18) 0%, rgba(244,63,94,0.04) 100%)'
          : 'linear-gradient(90deg, rgba(16,185,129,0.15) 0%, rgba(16,185,129,0.03) 100%)',
        borderBottom: `1px solid ${isUnsafe ? 'rgba(244,63,94,0.15)' : 'rgba(16,185,129,0.12)'}`,
      }}>
        {/* Index badge */}
        <span style={{
          fontFamily: 'monospace',
          fontSize: 12,
          fontWeight: 800,
          color: 'rgba(148,163,184,0.9)',
          background: 'rgba(255,255,255,0.07)',
          border: '1px solid rgba(255,255,255,0.12)',
          padding: '3px 9px',
          borderRadius: 7,
          letterSpacing: '0.04em',
        }}>
          #{String(index + 1).padStart(2, '0')}
        </span>

        {/* Status Badge */}
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 12px',
          borderRadius: 20,
          fontSize: 10,
          fontWeight: 900,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          background: pal.dim,
          color: pal.accent,
          border: `1px solid ${pal.border}`,
          boxShadow: isSelected ? `0 0 10px ${pal.accent}50` : 'none',
        }}>
          <span style={{ fontSize: 13 }}>{isUnsafe ? '⚠' : '🛡'}</span>
          {isUnsafe ? 'UNSAFE' : 'SAFE'}
        </span>
      </div>

      {/* ── BODY: Horizontal layout ───────────────────────────────── */}
      <div style={{
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 18,
        padding: '20px 18px 16px 20px',
      }}>

        {/* Score Ring */}
        <div style={{ position: 'relative', width: 90, height: 90, flexShrink: 0 }}>
          <svg width={90} height={90} style={{ position: 'absolute', inset: 0, transform: 'rotate(-90deg)' }}>
            <circle cx={45} cy={45} r={R + 6} fill="transparent" stroke={pal.accent} strokeWidth={1} opacity={isSelected ? 0.25 : 0.1} />
            <circle cx={45} cy={45} r={R} fill="transparent" stroke="rgba(255,255,255,0.07)" strokeWidth={SW + 1} />
            <circle
              cx={45} cy={45} r={R}
              fill="transparent"
              stroke={pal.accent}
              strokeWidth={SW + 1}
              strokeDasharray={circ}
              strokeDashoffset={offset}
              strokeLinecap="round"
              style={{ transition: 'stroke-dashoffset 0.9s cubic-bezier(0.4,0,0.2,1)', filter: `drop-shadow(0 0 6px ${pal.accent}90)` }}
            />
          </svg>
          {/* Center label */}
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{
              fontSize: 24,
              fontWeight: 900,
              color: pal.accent,
              lineHeight: 1,
              fontFamily: 'monospace',
              letterSpacing: '-0.02em',
              textShadow: `0 0 16px ${pal.accent}90`,
            }}>
              {s.risk_score}
            </span>
            <span style={{
              fontSize: 8,
              fontWeight: 700,
              color: 'rgba(148,163,184,0.55)',
              textTransform: 'uppercase',
              letterSpacing: '0.07em',
              marginTop: 3,
            }}>
              RISK
            </span>
          </div>
        </div>

        {/* Right: Date + meta info */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
          {/* Date row */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Calendar size={14} color={pal.accent} />
              <span style={{
                fontSize: 15,
                fontWeight: 800,
                color: '#f1f5f9',
                letterSpacing: '0.01em',
                lineHeight: 1.2,
              }}>
                {dateStr}
              </span>
            </div>
            <span style={{
              fontFamily: 'monospace',
              fontSize: 11,
              color: 'rgba(100,116,139,0.85)',
              letterSpacing: '0.05em',
              paddingLeft: 21,
            }}>
              {rawDate}
            </span>
          </div>

          {/* Category + Flags row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {/* Category badge */}
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              padding: '4px 10px',
              borderRadius: 8,
              fontSize: 10,
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              background: catStyle.bg,
              color: catStyle.color,
              border: `1px solid ${catStyle.border}`,
              flexShrink: 0,
            }}>
              <span style={{ fontSize: 12 }}>{catIcon}</span> {catLabel}
            </span>

            {/* Flags */}
            {s.flags.length > 0 ? (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '4px 10px',
                borderRadius: 8,
                fontSize: 10,
                fontWeight: 700,
                color: '#fca5a5',
                background: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.25)',
              }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#ef4444', display: 'inline-block', boxShadow: '0 0 5px #ef4444' }} />
                {s.flags.length} Flag{s.flags.length > 1 ? 's' : ''}
              </span>
            ) : (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '4px 10px',
                borderRadius: 8,
                fontSize: 10,
                fontWeight: 700,
                color: '#6ee7b7',
                background: 'rgba(16,185,129,0.1)',
                border: '1px solid rgba(16,185,129,0.22)',
              }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 5px #10b981' }} />
                Clean
              </span>
            )}
          </div>

          {/* Status code */}
          {s.status_code && (
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              fontSize: 11, color: 'rgba(148,163,184,0.65)',
            }}>
              <span style={{
                fontFamily: 'monospace', fontWeight: 700,
                color: s.status_code === 200 ? '#34d399' : s.status_code >= 400 ? '#f87171' : '#fbbf24',
                fontSize: 12,
              }}>HTTP {s.status_code}</span>
              <span>·</span>
              <span>Wayback Capture</span>
            </div>
          )}
        </div>

        {/* Arrow indicator */}
        <div style={{
          flexShrink: 0,
          width: 28, height: 28,
          borderRadius: '50%',
          background: isSelected ? `${pal.accent}25` : 'rgba(255,255,255,0.04)',
          border: `1px solid ${isSelected ? pal.accent + '60' : 'rgba(255,255,255,0.1)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'all 0.25s',
        }}>
          <svg width={12} height={12} viewBox="0 0 12 12" fill="none">
            <path d="M4 2.5L8 6L4 9.5" stroke={isSelected ? pal.accent : 'rgba(148,163,184,0.5)'} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      {/* ── BOTTOM PROGRESS BAR ──────────────────────────────────── */}
      <div style={{ height: 4, width: '100%', background: 'rgba(255,255,255,0.04)', overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${s.risk_score}%`,
          background: `linear-gradient(90deg, ${pal.accent}55, ${pal.accent})`,
          transition: 'width 0.9s cubic-bezier(0.4,0,0.2,1)',
          boxShadow: `0 0 8px ${pal.accent}90`,
        }} />
      </div>
    </div>
  );
}



/* ─── Main component ──────────────────────────────────────────── */
export default function SnapshotTimeline({ snapshots, activeSnapshot, onSelectSnapshot }: SnapshotTimelineProps) {
  const [localSelected, setLocalSelected] = useState<Snapshot | null>(null);

  if (!snapshots || snapshots.length === 0) return null;

  // Use externally-controlled selection if provided, else local
  const selected = activeSnapshot ?? localSelected ?? snapshots[0];

  const handleSelect = (s: Snapshot) => {
    setLocalSelected(s);
    onSelectSnapshot?.(s);
  };

  const chartData: ChartDataPoint[] = snapshots.map((s) => ({
    name: `${s.timestamp.slice(0, 4)}-${s.timestamp.slice(4, 6)}-${s.timestamp.slice(6, 8)}`,
    timestamp: s.timestamp,
    score: s.risk_score,
    url: s.original_url,
    status: s.status_code,
    flagsCount: s.flags.length,
    fullDate: formatDate(s.timestamp),
  }));

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: ChartDataPoint }> }) => {
    if (active && payload?.length) {
      const d = payload[0].payload;
      const rp = getRiskPalette(d.score, undefined);
      return (
        <div style={{
          background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)',
          padding: '12px 14px', borderRadius: 10, boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          backdropFilter: 'blur(8px)', fontSize: 12, minWidth: 160,
        }}>
          <p style={{ color: '#f1f5f9', fontWeight: 700, marginBottom: 8 }}>{d.fullDate}</p>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
            <span style={{ color: '#64748b' }}>Risk Score</span>
            <span style={{ color: rp.accent, fontWeight: 800 }}>{d.score}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
            <span style={{ color: '#64748b' }}>HTTP Status</span>
            <span style={{ color: '#a5b4fc', fontFamily: 'monospace', fontWeight: 700 }}>{d.status ?? 200}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
            <span style={{ color: '#64748b' }}>Risk Flags</span>
            <span style={{ color: d.flagsCount > 0 ? '#f87171' : '#34d399', fontWeight: 700 }}>{d.flagsCount} triggered</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-panel" style={{ padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 9, background: 'rgba(139,92,246,0.15)',
            border: '1px solid rgba(139,92,246,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Layers size={15} color="#a78bfa" />
          </div>
          <h3 style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 17, margin: 0 }}>Historical Snapshot Timeline</h3>
        </div>
        <p style={{ color: '#475569', fontSize: 13, margin: 0, paddingLeft: 42 }}>
          Risk trend across <span style={{ color: '#94a3b8', fontWeight: 600 }}>{snapshots.length}</span> Wayback captures —
          from <span style={{ color: '#94a3b8' }}>{chartData[0].name}</span> to <span style={{ color: '#94a3b8' }}>{chartData[chartData.length - 1].name}</span>.
          Select a snapshot to inspect its evidence.
        </p>
      </div>

      {/* Chart */}
      <div style={{ height: 220, width: '100%' }}>
        <ResponsiveContainer width="100%" height={220} minWidth={1}>
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.45} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.5} />
            <XAxis dataKey="name" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="score" stroke="#8b5cf6" strokeWidth={2.5} fillOpacity={1} fill="url(#scoreGradient)" dot={{ r: 3, fill: '#8b5cf6', strokeWidth: 0 }} activeDot={{ r: 5, fill: '#a78bfa', stroke: '#1e1b4b', strokeWidth: 2 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Split Panel: Tabs | Detail */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <Hash size={13} color="#475569" />
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569' }}>
            Analyzed Snapshot Details
          </span>
          <span style={{
            marginLeft: 4, padding: '1px 7px', borderRadius: 5, fontSize: 10, fontWeight: 700,
            background: 'rgba(139,92,246,0.15)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.2)',
          }}>{snapshots.length} captures</span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(380px, 460px) 1fr',
          gap: 24,
          alignItems: 'start',
        }}>
          {/* LEFT: Snapshot selector tabs */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            maxHeight: 820,
            overflowY: 'auto',
            paddingRight: 10,
          }}>
            {/* Legend strip */}
            <div style={{
              padding: '6px 12px', borderRadius: 8,
              background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.12)',
              fontSize: 10, color: '#6366f1', fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4,
            }}>
              <Shield size={11} />
              Click a snapshot to inspect its evidence →
            </div>
            {snapshots.map((s, i) => (
              <SnapshotTab
                key={s.timestamp}
                s={s}
                index={i}
                isSelected={selected?.timestamp === s.timestamp}
                onSelect={handleSelect}
              />
            ))}
          </div>

          {/* RIGHT: Detail panel */}
          <div style={{ minHeight: 680, position: 'sticky', top: 20 }}>
            {selected ? (
              <SnapshotDetailPanel s={selected} />
            ) : (
              <div style={{
                height: '100%', display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: 12,
                border: '1px dashed rgba(255,255,255,0.08)', borderRadius: 18,
                color: '#334155', fontSize: 13,
              }}>
                <AlertTriangle size={28} color="#334155" />
                <span>Select a snapshot from the left panel</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.8); }
        }
      `}</style>
    </div>
  );
}
