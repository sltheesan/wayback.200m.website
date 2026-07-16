import { Brain, CheckCircle, Clock } from 'lucide-react';
import { DomainAnalysisResponse } from '../types';

interface ExplainabilityCardProps {
  data: DomainAnalysisResponse;
}

const CATEGORY_STYLES: Record<string, { color: string; bg: string; icon: string }> = {
  gambling:  { color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/20', icon: '🎰' },
  adult:     { color: 'text-rose-400',   bg: 'bg-rose-500/10 border-rose-500/20',     icon: '🔞' },
  phishing_scam: { color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', icon: '🎣' },
  malware_hacking: { color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20',  icon: '💀' },
  illegal_pharmaceuticals: { color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20', icon: '💊' },
  safe: { color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', icon: '✅' },
};

const CONTAINER_STYLES: Record<string, string> = {
  gambling: 'border-l-4 border-l-orange-500 border-orange-500/20 bg-gradient-to-br from-orange-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(249,115,22,0.03)]',
  adult: 'border-l-4 border-l-rose-500 border-rose-500/20 bg-gradient-to-br from-rose-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(244,63,94,0.03)]',
  phishing_scam: 'border-l-4 border-l-amber-500 border-amber-500/20 bg-gradient-to-br from-amber-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(245,158,11,0.03)]',
  malware_hacking: 'border-l-4 border-l-rose-500 border-rose-500/20 bg-gradient-to-br from-rose-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(244,63,94,0.03)]',
  illegal_pharmaceuticals: 'border-l-4 border-l-violet-500 border-violet-500/20 bg-gradient-to-br from-violet-950/5 to-slate-900/10 shadow-[0_0_20px_rgba(139,92,246,0.03)]',
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
      <div className="flex flex-wrap items-start sm:items-center gap-3">
        <div className={`p-2.5 rounded-xl border shrink-0 ${style.bg}`}>
          <Brain size={20} className={style.color} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base sm:text-lg font-bold">AI Risk Explanation</h3>
          <p className="text-slate-400 text-xs mt-0.5">
            Automatically generated from content analysis and structural signals
          </p>
        </div>
        {confPct != null && (
          <span className={`px-3 py-1 rounded-full text-xs font-bold border ${style.bg} ${style.color} shrink-0`}>
            {confPct}% confidence
          </span>
        )}
      </div>

      {/* Narrative paragraph */}
      <div className={`p-4 rounded-xl border ${style.bg} relative overflow-hidden`}>
        <div className="absolute top-0 left-0 h-full w-1 rounded-l-xl" style={{
          background: cat === 'gambling' ? '#f97316' : cat === 'adult' ? '#ef4444' :
                      cat === 'phishing_scam' ? '#f59e0b' : cat === 'malware_hacking' ? '#ef4444' :
                      cat === 'safe' ? '#10b981' : '#8b5cf6'
        }} />
        <p className="text-sm text-slate-200 leading-relaxed pl-2 font-medium">
          {risk_narrative}
        </p>
      </div>

      {/* Meta chips */}
      <div className="flex flex-wrap gap-2">
        {risk_period && risk_period !== 'recently' && (
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
            <Clock size={12} className="text-slate-500" />
            <span className="font-semibold">Risk Period:</span>
            <span className="font-mono text-violet-400">{risk_period}</span>
          </div>
        )}
        <div className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold ${style.bg} ${style.color}`}>
          <span>{style.icon}</span>
          <span>{cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
        </div>
        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300 font-semibold uppercase tracking-wider">
          {risk_level}
        </div>
      </div>

      {/* Evidence bullets */}
      {evidence_bullets && evidence_bullets.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
            Evidence Summary
          </h4>
          <div className="space-y-1.5">
            {evidence_bullets.map((bullet, i) => (
              <div key={i} className="flex items-start space-x-2 text-xs text-slate-300">
                <CheckCircle size={13} className={`${style.color} mt-0.5 shrink-0`} />
                <span>{bullet}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
