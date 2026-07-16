import { Hash, Layers } from 'lucide-react';
import { Snapshot } from '../types';

interface IntelligencePanelProps {
  snapshot: Snapshot;
}

const CATEGORY_STYLES: Record<string, { label: string; bar: string; text: string; bg: string }> = {
  gambling: { label: 'Gambling / Betting', bar: 'bg-indigo-500', text: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' },
  adult: { label: 'Adult / Explicit Content', bar: 'bg-pink-500', text: 'text-pink-400', bg: 'bg-pink-500/10 border-pink-500/20' },
  phishing_scam: { label: 'Phishing / Scam', bar: 'bg-amber-500', text: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
  malware_hacking: { label: 'Malware / Hacking', bar: 'bg-rose-500', text: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20' },
  illegal_pharmaceuticals: { label: 'Illegal Pharmaceuticals', bar: 'bg-violet-500', text: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20' },
  safe: { label: 'Safe / Benign', bar: 'bg-emerald-500', text: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
};

export default function IntelligencePanel({ snapshot }: IntelligencePanelProps) {
  const ai = snapshot.ai_intelligence;
  
  // Collect categories from scores or list default
  const allScores = ai?.all_scores || {};
  const activeCategories = Object.entries(allScores).sort((a, b) => b[1] - a[1]);

  return (
    <div className="glass-panel p-6 sm:p-8 space-y-6">
      <div>
        <h3 className="text-lg font-bold">Snapshot Intelligence Scan</h3>
        <p className="text-slate-400 text-xs mt-0.5 font-medium">
          Captured Content Category Analysis: <span className="text-violet-400 font-bold uppercase">{snapshot.content_category || 'SAFE'}</span>
        </p>
      </div>

      {ai?.summary && (
        <div className="p-3 border border-slate-800 bg-slate-950/40 rounded-xl text-xs font-semibold text-slate-200">
          🔍 AI Verdict: "{ai.summary}"
        </div>
      )}

      {/* Category breakdown */}
      {activeCategories.length > 0 ? (
        <div className="space-y-3.5">
          <h4 className="text-[10px] uppercase tracking-wider font-extrabold text-slate-400 flex items-center">
            <Layers size={12} className="mr-1.5 text-violet-400" />
            AI Content Category Scores
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {activeCategories.map(([cat, score]) => {
              const styles = CATEGORY_STYLES[cat] || CATEGORY_STYLES.safe;
              const pct = Math.round(score * 100);

              return (
                <div key={cat} className="space-y-1 bg-slate-900/10 p-2.5 rounded-xl border border-slate-800/60">
                  <div className="flex justify-between text-[11px] font-bold">
                    <span className="text-slate-300">{styles.label}</span>
                    <span className={styles.text}>{pct}%</span>
                  </div>
                  <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-800/40">
                    <div className={`${styles.bar} h-full rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="text-center py-4 border border-dashed border-slate-900 rounded-lg text-slate-500 text-xs">
          No significant risk patterns detected by the AI classification engine.
        </div>
      )}

      {/* Flag / Evidence List */}
      <div className="space-y-3">
        <h4 className="text-[10px] uppercase tracking-wider font-extrabold text-slate-400 flex items-center">
          <Hash size={12} className="mr-1.5 text-violet-400" />
          Evidence Log ({snapshot.flags.length} items)
        </h4>
        {snapshot.flags.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
            {snapshot.flags.map((flag, idx) => {
              return (
                <div key={idx} className="flex justify-between items-center p-2 rounded-lg bg-slate-900/25 border border-slate-800/80 text-xs">
                  <div className="space-y-0.5">
                    <span className="font-bold text-white font-mono">"{flag.keyword}"</span>
                    <span className="text-[9px] text-slate-500 block uppercase font-bold tracking-wider">
                      {flag.category.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-rose-400 block font-mono">+{flag.weight}</span>
                    <span className="text-[9px] text-slate-500 block">{flag.match_count} matches</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-4 border border-dashed border-slate-900 rounded-lg text-slate-500 text-xs">
            No keyword triggers. Document matches clean baseline signatures.
          </div>
        )}
      </div>
    </div>
  );
}
