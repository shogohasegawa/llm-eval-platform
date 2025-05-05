/**
 * 評価指標の型定義
 */

export type MetricType = 'accuracy' | 'precision' | 'recall' | 'f1' | 'bleu' | 'rouge' | 'exact_match' | 'semantic_similarity' | 'latency' | 'token_count' | 'custom';

export interface Metric {
  id: string;
  name: string;
  type: MetricType;
  description?: string;
  isHigherBetter: boolean; // 値が高いほど良いか
  parameters?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

export interface MetricFormData {
  name: string;
  type: MetricType;
  description?: string;
  isHigherBetter: boolean;
  parameters?: Record<string, any>;
}

export interface LeaderboardEntry {
  rank: number;
  inferenceId: string;
  inferenceName: string;
  providerId: string;
  providerName: string;
  modelId: string;
  modelName: string;
  datasetId: string;
  datasetName: string;
  metrics: Record<string, number>;
  createdAt: Date;
}

export interface LeaderboardFilterOptions {
  datasetId?: string;
  providerId?: string;
  modelId?: string;
  metricId?: string;
  limit?: number;
}
