export interface AnalysisFlag {
  category: string;
  keyword: string;
  weight: number;
  match_count: number;
  element?: string | null;
  matched_text?: string | null;
  snippet?: string | null;
  position?: number | null;
}

export interface DetectorResult {
  detector: string;
  signal: 'low' | 'medium' | 'high';
  [key: string]: unknown;
}

export interface AIIntelligence {
  primary_category: string | null;
  confidence: number | null;
  all_scores: Record<string, number> | null;
  detected_language: string | null;
  summary: string | null;
  detectors: DetectorResult[] | null;
  detector_boost: number | null;
}

export interface Snapshot {
  timestamp: string;
  original_url: string;
  status_code: number | null;
  mime_type: string | null;
  risk_score: number;
  detected_language: string | null;
  content_category: string | null;
  category_confidence: number | null;
  content_summary: string | null;
  evidence_url?: string | null;
  ai_intelligence: AIIntelligence | null;
  flags: AnalysisFlag[];
}

export interface TimelineEntry {
  year: number;
  category: string;
  category_label: string | null;
  category_icon: string | null;
  risk_score: number;
  peak_score: number;
  snapshot_count: number;
  summary: string | null;
}

export interface ThreatIntel {
  provider: string;
  status: 'safe' | 'malicious' | 'suspicious' | 'unknown' | 'not_configured' | 'error';
  confidence: number | null;
  verdict: string | null;
  screenshot_url?: string | null;
  raw_response?: string | null;
  fetched_at: string | null;
}

export interface DomainAnalysisResponse {
  domain: string;
  risk_score: number;
  risk_level: string;
  peak_score: number;
  avg_score: number;
  category_confidence: Record<string, number>;
  flags: string[];
  snapshots_checked: number;
  last_updated: string;
  history_summary?: Array<{
    timestamp: string;
    year: string;
    risk_score: number;
    categories: string[];
  }>;
  snapshots: Snapshot[];
  // Intelligence enrichments
  primary_category?: string | null;
  risk_narrative?: string | null;
  evidence_bullets?: string[] | null;
  risk_period?: string | null;
  ai_confidence?: number | null;
  timeline?: TimelineEntry[] | null;
  threat_intel?: ThreatIntel[] | null;
  threat_overall?: string | null;
}

export interface SystemStatus {
  status: string;
  postgres: string;
  redis: string;
}

export interface RecentDomain {
  domain: string;
  risk_score: number;
  risk_level: string;
  last_analyzed_at: string;
}

export interface GlobalStats {
  total_analyzed: number;
  risk_breakdown: {
    SAFE: number;
    MEDIUM: number;
    HIGH: number;
    UNSAFE?: number;
    UNKNOWN?: number;
  };
  recent_domains: RecentDomain[];
}
