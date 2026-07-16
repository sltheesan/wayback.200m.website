import axios from 'axios';
import { DomainAnalysisResponse, GlobalStats } from '../types';

// In production (Docker), the frontend is served by Nginx which proxies /api/ → backend.
// Using a relative URL ensures all requests go through Nginx — no CORS issues.
const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  /**
   * Analyzes a single domain.
   */
  async analyzeDomain(domain: string, forceRefresh: boolean = false): Promise<DomainAnalysisResponse> {
    const body = {
      domain,
      force_refresh: forceRefresh,
    };
    const response = await apiClient.post<DomainAnalysisResponse>('/domains/analyze', body);
    return response.data;
  },

  /**
   * Fetches aggregate analysis statistics.
   */
  async getStats(): Promise<GlobalStats> {
    const response = await apiClient.get<GlobalStats>('/domains/stats');
    return response.data;
  },

  /**
   * Submits a list of domains for bulk background analysis.
   */
  async bulkAnalyze(domains: string[]): Promise<{ task_id: string; message: string }> {
    const body = { domains };
    const response = await apiClient.post<{ task_id: string; message: string }>('/domains/bulk-analyze', body);
    return response.data;
  },

  /**
   * Retrieves the status and results of a Celery background task.
   */
  async getTaskStatus(taskId: string): Promise<any> {
    const response = await apiClient.get<any>(`/analysis/task/${taskId}`);
    return response.data;
  },

  /**
   * Fetches risk keywords and weights.
   */
  async getRules(): Promise<Record<string, Record<string, number>>> {
    const response = await apiClient.get<Record<string, Record<string, number>>>('/analysis/rules');
    return response.data;
  },

  /**
   * Queries system health status via Nginx proxy.
   */
  async getHealth(): Promise<any> {
    const response = await axios.get<any>('/health');
    return response.data;
  },
};

export default apiService;
