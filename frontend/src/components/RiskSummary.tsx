import { ShieldCheck, ShieldAlert, Calendar, Layers } from 'lucide-react';
import { DomainAnalysisResponse } from '../types';

interface RiskSummaryProps {
  data: DomainAnalysisResponse;
}

export default function RiskSummary({ data }: RiskSummaryProps) {
  const {
    domain,
    risk_score,
    risk_level,
    snapshots_checked,
    last_updated,
    peak_score,
    avg_score,
    category_confidence
  } = data;

  // Configuration for threat colors
  const getRiskDetails = (level: string) => {
    switch (level) {
      case 'HIGH':
      case 'UNSAFE':
        return {
          color: 'text-rose-400 border-rose-500/20 bg-rose-500/5',
          fill: '#ef4444',
          icon: <ShieldAlert className="text-rose-400" size={28} />,
          bg: 'bg-rose-500',
          desc: 'Threat detected. Historical snapshots contain gambling, adult, or fraudulent/phishing content.'
        };
      case 'MEDIUM':
        return {
          color: 'text-amber-400 border-amber-500/20 bg-amber-500/5',
          fill: '#f59e0b',
          icon: <ShieldAlert className="text-amber-400" size={28} />,
          bg: 'bg-amber-500',
          desc: 'Moderate risk. Detected some flagged categories. Historical records show irregular changes or minor risk flags.'
        };
      case 'UNKNOWN':
        return {
          color: 'text-violet-400 border-violet-500/20 bg-violet-500/5',
          fill: '#8b5cf6',
          icon: <ShieldAlert className="text-violet-400" size={28} />,
          bg: 'bg-violet-500',
          desc: 'Insufficient data. No historical snapshots exist, or all archive captures were inaccessible.'
        };
      default:
        return {
          color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5',
          fill: '#10b981',
          icon: <ShieldCheck className="text-emerald-400" size={28} />,
          bg: 'bg-emerald-500',
          desc: 'No significant risk patterns detected. Historical content matches safe category signatures.'
        };
    }
  };

  const details = getRiskDetails(risk_level);

  // SVG circular gauge properties
  const radius = 60;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (risk_score / 100) * circumference;

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return isoString;
    }
  };

  // Get categories with confidence scores
  const activeCategories = category_confidence
    ? Object.entries(category_confidence).filter(([_, score]) => score > 0)
    : [];

  return (
    <div className="glass-panel p-5 sm:p-8 flex flex-col md:flex-row items-center md:items-start space-y-6 md:space-y-0 md:space-x-8">
      
      {/* Circle Gauge Component */}
      <div className="flex flex-col items-center justify-center w-full md:min-w-[180px] md:w-auto">
        <div className="relative">
          <svg className="w-32 h-32 sm:w-36 sm:h-36">
            {/* Background Circle */}
            <circle
              className="text-slate-800"
              strokeWidth={strokeWidth}
              stroke="currentColor"
              fill="transparent"
              r={radius}
              cx="72"
              cy="72"
            />
            {/* Progress Circle */}
            <circle
              className="progress-ring__circle"
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              stroke={details.fill}
              fill="transparent"
              r={radius}
              cx="72"
              cy="72"
            />
          </svg>
          {/* Centered Score Text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-extrabold tracking-tight text-white">{risk_score}</span>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-widest">Risk Score</span>
          </div>
        </div>

        {/* Score Composition Sub-panel */}
        <div className="mt-4 w-full border border-slate-800/80 bg-slate-900/20 p-3 rounded-xl flex flex-col space-y-1.5 text-[11px] font-medium text-slate-400">
          <div className="flex justify-between">
            <span>Peak Score (60%):</span>
            <span className="font-bold text-slate-200">{peak_score}</span>
          </div>
          <div className="flex justify-between">
            <span>Avg Score (40%):</span>
            <span className="font-bold text-slate-200">{avg_score}</span>
          </div>
          <div className="border-t border-slate-800/60 my-1 pt-1 flex justify-between font-bold text-[10px] uppercase text-slate-300">
            <span>Weighted Total:</span>
            <span className="text-violet-400">{risk_score}</span>
          </div>
        </div>
      </div>

      {/* Domain Details */}
      <div className="flex-1 flex flex-col justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <h2 className="text-2xl font-black tracking-tight text-white">{domain}</h2>
            <div className={`px-3 py-1 rounded-full text-xs font-bold border uppercase tracking-wider flex items-center space-x-1.5 ${details.color}`}>
              {details.icon}
              <span>{risk_level} RISK</span>
            </div>
          </div>
          
          <p className="text-slate-300 text-sm leading-relaxed mb-4">
            {details.desc}
          </p>

          {/* Threat Category Confidence */}
          {activeCategories.length > 0 && (
            <div className="space-y-2.5 mb-6 pt-4 border-t border-slate-800/60">
              <h4 className="text-[10px] uppercase tracking-wider font-extrabold text-slate-400">
                Threat Category Confidence
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
                {activeCategories.map(([cat, score]) => {
                  const barColor = cat === 'gambling' ? 'bg-purple-500' :
                                   cat === 'adult' ? 'bg-pink-500' :
                                   cat === 'phishing_scam' ? 'bg-amber-500' :
                                   cat === 'malware_hacking' ? 'bg-rose-500' : 
                                   cat === 'illegal_pharmaceuticals' ? 'bg-violet-500' : 'bg-red-500';
                  
                  const catLabel = cat.replace('_', ' ').replace('phishing scam', 'phishing / scam').toUpperCase();
                  
                  return (
                    <div key={cat} className="space-y-1">
                      <div className="flex justify-between text-[10px] font-bold">
                        <span className="text-slate-300">{catLabel}</span>
                        <span className="text-slate-400">{score}%</span>
                      </div>
                      <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden border border-slate-800/40">
                        <div className={`${barColor} h-full rounded-full transition-all duration-500`} style={{ width: `${score}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Info badges */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-4 border-t border-slate-800/60">
          <div className="flex items-center space-x-2 text-slate-400">
            <Layers size={16} className="text-slate-500" />
            <div>
              <p className="text-slate-500 font-semibold uppercase tracking-wider text-[9px]">Snapshots Sampled</p>
              <p className="text-slate-200 font-medium text-sm">{snapshots_checked} Wayback Captures</p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-slate-400">
            <Calendar size={16} className="text-slate-500" />
            <div>
              <p className="text-slate-500 font-semibold uppercase tracking-wider text-[9px]">Last Analyzed</p>
              <p className="text-slate-200 font-medium text-sm">{formatDate(last_updated)}</p>
            </div>
          </div>
        </div>
      </div>
      
    </div>
  );
}
