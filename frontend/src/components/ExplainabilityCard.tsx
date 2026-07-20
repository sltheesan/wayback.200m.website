import { Brain, CheckCircle, Clock } from 'lucide-react';
import { DomainAnalysisResponse } from '../types';

interface ExplainabilityCardProps {
  data: DomainAnalysisResponse;
}

const CATEGORY_STYLES: Record<string, { color: string; bg: string; icon: string }> = {
  gambling:  { color: '#fb7185', bg: 'bg-rose-500/10 border-rose-500/20',     icon: '🔞' },
  adult:     { color: '#fb7185', bg: 'bg-rose-500/10 border-rose-500/20',     icon: '🔞' },
  phishing_scam: { color: '#fbbf24', bg: 'bg-amber-500/10 border-amber-500/20', icon: '🎣' },
  malware_hacking: { color: '#fb7185', bg: 'bg-rose-500/10 border-rose-500/20',  icon: '💀' },
  illegal_pharmaceuticals: { color: '#a78bfa', bg: 'bg-violet-500/10 border-violet-500/20', icon: '💊' },
  gaming: { color: '#22d3ee', bg: 'bg-cyan-500/10 border-cyan-500/20', icon: '🎮' },
  safe: { color: '#34d399', bg: 'bg-emerald-500/10 border-emerald-500/20', icon: '✅' },
};

const CONTAINER_STYLES: Record<string, string> = {
  gambling: 'border-l-4 border-l-rose-500 border-rose-500/20 bg-gradient-to-br from-rose-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(244,63,94,0.03)]',
  adult: 'border-l-4 border-l-rose-500 border-rose-500/20 bg-gradient-to-br from-rose-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(244,63,94,0.03)]',
  phishing_scam: 'border-l-4 border-l-amber-500 border-amber-500/20 bg-gradient-to-br from-amber-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(245,158,11,0.03)]',
  malware_hacking: 'border-l-4 border-l-rose-500 border-rose-500/20 bg-gradient-to-br from-rose-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(244,63,94,0.03)]',
  illegal_pharmaceuticals: 'border-l-4 border-l-violet-500 border-violet-500/20 bg-gradient-to-br from-violet-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(139,92,246,0.03)]',
  gaming: 'border-l-4 border-l-cyan-500 border-cyan-500/20 bg-gradient-to-br from-cyan-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(6,182,212,0.03)]',
  safe: 'border-l-4 border-l-emerald-500 border-emerald-500/20 bg-gradient-to-br from-emerald-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(16,185,129,0.03)]',
};

export default function ExplainabilityCard({ data }: ExplainabilityCardProps) {
  const {
    risk_narrative, evidence_bullets, primary_category,
    ai_confidence, risk_period, risk_level,
  } = data;

  if (!risk_narrative) return null;

  const cat = primary_category || 'safe';
  const style = CATEGORY_STYLES[cat] || CATEGORY_STYLES['safe'];
  const containerStyle = CONTAINER_STYLES[cat] || CONTAINER_STYLES['safe'];
  const confPct = ai_confidence != null ? Math.round(ai_confidence * 100) : null;

  return (
    <div className={`glass-panel p-6 sm:p-8 space-y-6 transition-all duration-300 ${containerStyle}`}>
      {/* Header */}
      <div className="flex flex-wrap items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl border shrink-0 ${style.bg}`}>
            <Brain size={20} style={{ color: style.color }} />
          </div>
          <div className="text-left">
            <h3 className="text-base sm:text-lg font-bold text-white">AI Risk Explanation</h3>
            <p className="text-slate-400 text-xs mt-0.5">
              Automatically generated from content analysis and structural signals
            </p>
          </div>
        </div>
        {confPct != null && (
          <span className="px-3 py-1 rounded-full text-xs font-bold border shrink-0" style={{ backgroundColor: `${style.color}15`, borderColor: `${style.color}30`, color: style.color }}>
            {confPct}% confidence
          </span>
        )}
      </div>

      {/* Two Column Grid layout to use full screen width creatively */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8 items-stretch">
        
        {/* Left Column: AI explanation narrative & metadata */}
        <div className="flex flex-col justify-between space-y-4">
          <div className="space-y-3 text-left">
            <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              Analysis Narrative
            </h4>
            <div className={`p-5 rounded-xl border ${style.bg} relative overflow-hidden min-h-[140px] flex flex-col justify-center`}>
              <div className="absolute top-0 left-0 h-full w-1 rounded-l-xl" style={{ backgroundColor: style.color }} />
              <p className="text-sm text-slate-200 leading-relaxed pl-2 font-medium">
                {risk_narrative}
              </p>
            </div>
          </div>

          <div className="space-y-4 pt-2">
            {/* Confidence bar indicator */}
            {confPct != null && (
              <div className="space-y-1.5 text-left">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-400">AI Classification Strength</span>
                  <span style={{ color: style.color }}>{confPct}%</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-900">
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${confPct}%`, backgroundColor: style.color }} />
                </div>
              </div>
            )}

            {/* Meta chips row */}
            <div className="flex flex-wrap gap-2">
              {risk_period && risk_period !== 'recently' && (
                <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
                  <Clock size={12} className="text-slate-500" />
                  <span className="font-semibold">Risk Period:</span>
                  <span className="font-mono text-violet-400">{risk_period}</span>
                </div>
              )}
              <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold" style={{ backgroundColor: `${style.color}15`, borderColor: `${style.color}30`, color: style.color }}>
                <span>{style.icon}</span>
                <span>{cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
              </div>
              <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300 font-semibold uppercase tracking-wider">
                {risk_level}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: AI detected evidence bullets */}
        <div className="flex flex-col space-y-3 text-left">
          <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
            Detected Evidence
          </h4>
          <div className="p-5 bg-slate-950/40 border border-slate-900 rounded-xl flex-1 flex flex-col justify-start">
            {evidence_bullets && evidence_bullets.length > 0 ? (
              <div className="space-y-3 w-full">
                {evidence_bullets.map((bullet, i) => (
                  <div key={i} className="flex items-start space-x-3 text-xs text-slate-300 bg-slate-900/20 p-3 rounded-lg border border-slate-800/40 hover:border-slate-800/80 transition-colors">
                    <CheckCircle size={15} style={{ color: style.color }} className="mt-0.5 shrink-0" />
                    <span className="leading-relaxed">{bullet}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center text-slate-500 space-y-2 flex-1 w-full">
                <span className="text-xl">🔍</span>
                <span className="text-xs">No explicit evidence flags triggered. Classification is based on general heuristic evaluation.</span>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
