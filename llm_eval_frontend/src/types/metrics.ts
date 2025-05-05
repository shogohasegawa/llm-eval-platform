/**
 * 評価指標の型定義
 */

export type MetricType = string;

// メトリックパラメータの情報
export interface MetricParameterInfo {
  type: string;
  description?: string;
  default?: any;
  required?: boolean;
  enum?: any[];
}

// 利用可能なメトリックタイプの情報
export interface MetricTypeInfo {
  name: string;
  description?: string;
  parameters?: Record<string, MetricParameterInfo>;
  is_higher_better: boolean;
}

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
  is_higher_better?: boolean; // バックエンド用のスネークケースバージョン
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
