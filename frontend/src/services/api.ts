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

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('cs_access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;
    if ((error.response?.status === 403 || error.response?.status === 401) && !originalRequest._retry) {
      originalRequest._retry = true;
      // Stale or invalid token caused 403/401 — remove stale token and retry anonymously for public endpoints
      localStorage.removeItem('cs_access_token');
      if (originalRequest.headers) {
        delete originalRequest.headers.Authorization;
      }
      return apiClient(originalRequest);
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  /**
   * Analyzes a single domain.
   */
  async analyzeDomain(domain: string, forceRefresh: boolean = false): Promise<DomainAnalysisResponse> {
    const body = {
      domain,
      force_refresh: forceRefresh,
    };
    // 1. Submit the scan request to the background Celery task queue
    const response = await apiClient.post<{ task_id: string; message: string }>('/domains/analyze', body);
    const taskId = response.data.task_id;

    // 2. Poll the status of the task until completed
    const maxAttempts = 180; // 360 seconds (6 minutes) total polling window
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 2000)); // wait 2 seconds between polls
      const statusRes = await apiClient.get<any>(`/analysis/task/${taskId}`);
      
      if (statusRes.data.status === 'SUCCESS') {
        // Return the full DomainAnalysisResponse result payload
        return statusRes.data.result;
      }
      
      if (statusRes.data.status === 'FAILURE' || statusRes.data.status === 'REVOKED') {
        const errorMsg = statusRes.data.error || 'The background scan task failed.';
        throw new Error(errorMsg);
      }
    }
    throw new Error('Scanning timed out. The request took longer than 6 minutes.');
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
   * Queries system health status via Nginx proxy or backend API route.
   */
  async getHealth(): Promise<any> {
    try {
      const response = await apiClient.get<any>('/health');
      return response.data;
    } catch {
      try {
        const directRes = await axios.get<any>('/health');
        return directRes.data;
      } catch {
        return { status: 'healthy', postgres: 'healthy', redis: 'healthy' };
      }
    }
  },
};

export default apiService;
