import { apiClient } from './client';
import { Metric, MetricFormData, LeaderboardEntry, LeaderboardFilterOptions } from '../types/metrics';

/**
 * 評価指標API
 */
export const metricsApi = {
  // 評価指標一覧の取得
  getMetrics: async (): Promise<Metric[]> => {
    return apiClient.get<Metric[]>('/metrics');
  },

  // 特定の評価指標の取得
  getMetric: async (id: string): Promise<Metric> => {
    return apiClient.get<Metric>(`/metrics/${id}`);
  },

  // 評価指標の作成
  createMetric: async (data: MetricFormData): Promise<Metric> => {
    return apiClient.post<Metric>('/metrics', data);
  },

  // 評価指標の更新
  updateMetric: async (id: string, data: MetricFormData): Promise<Metric> => {
    return apiClient.put<Metric>(`/metrics/${id}`, data);
  },

  // 評価指標の削除
  deleteMetric: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/metrics/${id}`);
  },

  // リーダーボードデータの取得
  getLeaderboard: async (filters?: LeaderboardFilterOptions): Promise<LeaderboardEntry[]> => {
    return apiClient.get<LeaderboardEntry[]>('/leaderboard', { params: filters });
  },

  // 推論に評価指標を適用
  applyMetricsToInference: async (inferenceId: string, metricIds: string[]): Promise<void> => {
    return apiClient.post<void>(`/inferences/${inferenceId}/apply-metrics`, { metricIds });
  },

  // リーダーボードデータのエクスポート（CSVファイル）
  exportLeaderboard: async (filters?: LeaderboardFilterOptions): Promise<Blob> => {
    return apiClient.getBlob('/leaderboard/export', { params: filters });
  },
};
