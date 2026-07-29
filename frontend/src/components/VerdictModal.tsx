import { useEffect } from 'react';
import { ShieldAlert, ShieldCheck, AlertTriangle, CheckCircle2, X, Sparkles, ArrowRight, Zap } from 'lucide-react';
import { DomainAnalysisResponse } from '../types';

interface VerdictModalProps {
  data: DomainAnalysisResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onExploreTimeline?: () => void;
}

export default function VerdictModal({ data, isOpen, onClose, onExploreTimeline }: VerdictModalProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen || !data) return null;

  const { domain, risk_score, risk_level, primary_category, category_confidence, snapshots } = data;

  const activeCategories = category_confidence
    ? Object.entries(category_confidence).filter(([_, score]) => score > 0)
    : [];
  const primaryCat = primary_category || (activeCategories.length > 0 ? activeCategories[0][0] : 'safe');

  const isUnsafe = risk_level === 'HIGH' || risk_level === 'UNSAFE' || risk_score >= 65 || (primaryCat !== 'safe' && primaryCat !== 'unknown');
  const isSafe = risk_level === 'SAFE' || (risk_score < 40 && (primaryCat === 'safe' || primaryCat === 'unknown'));

  const totalFlagsCount = snapshots ? snapshots.reduce((acc, s) => acc + (s.flags?.length || 0), 0) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Dark backdrop blur overlay */}
      <div 
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-md transition-opacity duration-300" 
        onClick={onClose}
      />

      {/* Modal Card Window */}
      <div className={`relative w-full max-w-2xl rounded-2xl border bg-slate-900/95 shadow-2xl overflow-hidden transition-all duration-300 transform scale-100 z-10 ${
        isUnsafe 
          ? 'border-rose-500/40 shadow-[0_0_60px_rgba(244,63,94,0.25)]' 
          : isSafe 
          ? 'border-emerald-500/40 shadow-[0_0_60px_rgba(16,185,129,0.25)]' 
          : 'border-amber-500/40 shadow-[0_0_60px_rgba(245,158,11,0.25)]'
      }`}>

        {/* Ambient Top Glow Line */}
        <div className={`h-1.5 w-full ${
          isUnsafe ? 'bg-gradient-to-r from-rose-600 via-rose-400 to-rose-600' :
          isSafe ? 'bg-gradient-to-r from-emerald-600 via-emerald-400 to-emerald-600' :
          'bg-gradient-to-r from-amber-600 via-amber-400 to-amber-600'
        }`} />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white transition-all duration-200 z-20"
          title="Close Verdict Window"
        >
          <X size={18} />
        </button>

        {/* Modal Body */}
        <div className="p-6 sm:p-8 space-y-6">

          {/* Header Badge & Title */}
          <div className="flex flex-col items-center text-center space-y-3 relative">
            
            {/* Hologram Icon Container */}
            <div className="relative">
              <div className={`w-20 h-20 rounded-2xl flex items-center justify-center border-2 transition-transform duration-500 hover:scale-105 ${
                isUnsafe 
                  ? 'bg-rose-500/15 border-rose-500/40 text-rose-400 shadow-[0_0_30px_rgba(244,63,94,0.3)]' 
                  : isSafe 
                  ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400 shadow-[0_0_30px_rgba(16,185,129,0.3)]' 
                  : 'bg-amber-500/15 border-amber-500/40 text-amber-400 shadow-[0_0_30px_rgba(245,158,11,0.3)]'
              }`}>
                {isUnsafe ? (
                  <ShieldAlert size={44} className="animate-pulse" />
                ) : isSafe ? (
                  <ShieldCheck size={44} />
                ) : (
                  <AlertTriangle size={44} />
                )}
              </div>
              <div className={`absolute -bottom-2 -right-2 p-1.5 rounded-full border text-[10px] font-extrabold ${
                isUnsafe ? 'bg-rose-950 border-rose-500 text-rose-300' : 'bg-emerald-950 border-emerald-500 text-emerald-300'
              }`}>
                {isUnsafe ? 'RISK' : 'SAFE'}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-center gap-2">
                <Sparkles size={14} className={isUnsafe ? 'text-rose-400' : 'text-emerald-400'} />
                <span className={`text-xs font-extrabold uppercase tracking-wider ${
                  isUnsafe ? 'text-rose-400' : isSafe ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  ChronoSentinel Security Verdict
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white mt-1 tracking-tight">
                {isUnsafe ? 'HIGH RISK THREAT DETECTED' : isSafe ? 'SECURITY VERIFIED SAFE' : 'MODERATE RISK WARNING'}
              </h2>
              <p className="text-slate-400 text-xs sm:text-sm mt-1 font-medium font-mono">
                Target Domain: <span className="text-white font-extrabold underline decoration-slate-700">{domain}</span>
              </p>
            </div>
          </div>

          {/* Key Metrics Row */}
          <div className="grid grid-cols-3 gap-3 text-center">
            
            {/* Risk Score Pill */}
            <div className={`p-3 rounded-xl border flex flex-col items-center justify-center ${
              isUnsafe ? 'bg-rose-950/30 border-rose-500/30' : isSafe ? 'bg-emerald-950/30 border-emerald-500/30' : 'bg-amber-950/30 border-amber-500/30'
            }`}>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Risk Score</span>
              <span className={`text-2xl font-black ${isUnsafe ? 'text-rose-400' : isSafe ? 'text-emerald-400' : 'text-amber-400'}`}>
                {risk_score} <span className="text-xs text-slate-500">/100</span>
              </span>
            </div>

            {/* Classification */}
            <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/50 flex flex-col items-center justify-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Classification</span>
              <span className="text-sm font-extrabold text-slate-200 mt-1 capitalize">
                {primaryCat.replace(/_/g, ' ')}
              </span>
            </div>

            {/* Total Flags */}
            <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/50 flex flex-col items-center justify-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Evidence Flags</span>
              <span className="text-sm font-extrabold text-slate-200 mt-1">
                {totalFlagsCount} Items
              </span>
            </div>

          </div>

          {/* Verdict Insights Box */}
          <div className={`p-4 sm:p-5 rounded-xl border text-left space-y-3 ${
            isUnsafe 
              ? 'bg-rose-950/20 border-rose-500/30 text-rose-200' 
              : isSafe 
              ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200' 
              : 'bg-amber-950/20 border-amber-500/30 text-amber-200'
          }`}>
            <h4 className="text-xs font-black uppercase tracking-wider flex items-center gap-2">
              <Zap size={14} className={isUnsafe ? 'text-rose-400' : 'text-emerald-400'} />
              <span>Security Summary & Intelligence Findings</span>
            </h4>
            <p className="text-xs leading-relaxed text-slate-300 font-medium">
              {isUnsafe ? (
                `Warning: ChronoSentinel analysis scanned ${snapshots?.length || 0} historical snapshots for ${domain} and detected malicious indicators. Content records matched ${primaryCat.replace(/_/g, ' ')} threat signatures.`
              ) : isSafe ? (
                `Verified Clean: ChronoSentinel completed deep historical content scanning for ${domain} across ${snapshots?.length || 0} archive records. Zero threat signatures, phishing lures, or illegal categories were detected.`
              ) : (
                `Moderate Caution: Historical scanning detected minor content irregularities or category score shifts for ${domain}. Proceed with standard security verification.`
              )}
            </p>
          </div>

          {/* Action Directives Bullet List */}
          <div className="space-y-2 text-left">
            <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              Recommended Security Directives
            </h4>
            <div className="space-y-2">
              {isUnsafe ? (
                <>
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-rose-950/30 border border-rose-500/20 text-xs text-rose-200">
                    <span className="text-rose-400 font-bold shrink-0">1.</span>
                    <span>Do <strong>NOT</strong> enter credentials or personal data if accessing this domain.</span>
                  </div>
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300">
                    <span className="text-slate-400 font-bold shrink-0">2.</span>
                    <span>Review historical timeline snapshots to inspect exact flagged keywords & redirects.</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-500/20 text-xs text-emerald-200">
                    <CheckCircle2 size={15} className="text-emerald-400 mt-0.5 shrink-0" />
                    <span>Domain maintains a <strong>100% clean baseline</strong> historical archive footprint.</span>
                  </div>
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300">
                    <CheckCircle2 size={15} className="text-slate-400 mt-0.5 shrink-0" />
                    <span>Safe for legitimate web browsing and domain reputation verification.</span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t border-slate-800/80">
            <button
              onClick={onClose}
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition-all cursor-pointer"
            >
              Dismiss Verdict
            </button>
            <button
              onClick={() => {
                onClose();
                if (onExploreTimeline) onExploreTimeline();
              }}
              className={`w-full sm:w-auto px-6 py-2.5 rounded-xl text-xs font-extrabold text-white flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer ${
                isUnsafe 
                  ? 'bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 shadow-rose-600/30' 
                  : 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 shadow-emerald-600/30'
              }`}
            >
              <span>Explore Timeline Evidence</span>
              <ArrowRight size={14} />
            </button>
          </div>

        </div>

      </div>
    </div>
  );
}
