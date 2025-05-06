import { apiClient } from './client';
import { Metric, LeaderboardEntry, LeaderboardFilterOptions, MetricTypeInfo } from '../types/metrics';

/**
 * 評価指標API
 */
export const metricsApi = {
  // 組み込み評価指標一覧の取得
  getBuiltinMetrics: async (): Promise<Metric[]> => {
    try {
      const response = await apiClient.get<{metrics: Metric[]}>('/api/v1/metrics/available');
      
      // 応答データの型変換を確実に行う
      const metrics = response.metrics || [];
      
      // データを適切に処理してブール値を確保
      return metrics.map(metric => {
        console.log('処理前のmetric:', metric);
        // is_higher_betterとisHigherBetterの両方をチェック
        const isHigherBetterValue = 
          metric.is_higher_better !== undefined ? Boolean(metric.is_higher_better) : 
          metric.isHigherBetter !== undefined ? Boolean(metric.isHigherBetter) : 
          true; // デフォルト値
        
        console.log(`metric ${metric.name}: is_higher_better=${metric.is_higher_better}, isHigherBetter=${metric.isHigherBetter}, 変換後=${isHigherBetterValue}`);
        
        return {
          ...metric,
          isHigherBetter: isHigherBetterValue
        };
      });
    } catch (error) {
      console.error('組み込み評価指標の取得に失敗しました:', error);
      throw error;
    }
  },
  
  // 指標のソースコードを取得
  getMetricCode: async (metricName: string): Promise<{filename: string, path: string, code: string, class_name: string}> => {
    return apiClient.get<{filename: string, path: string, code: string, class_name: string}>(`/api/v1/metrics/available/${metricName}/code`);
  },
  
  // カスタム評価指標をアップロード
  uploadMetricFile: async (file: File): Promise<{message: string, filename: string, path: string, metrics: string}> => {
    // FormDataを使用してファイルをアップロード
    const formData = new FormData();
    formData.append('file', file);
    
    // Content-Typeを設定しない（ブラウザが自動設定）
    const response = await apiClient.post<{message: string, filename: string, path: string, metrics: string}>('/api/v1/metrics/upload', formData, {
      headers: {
        // multipart/form-dataにする必要がある（自動設定される）
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response;
  },

  // カスタム評価指標一覧の取得
  getCustomMetrics: async (): Promise<Metric[]> => {
    try {
      const response = await apiClient.get<{metrics: Metric[]}>('/api/v1/metrics');
      
      // 応答データの型変換を確実に行う
      const metrics = response.metrics || [];
      
      // データを適切に処理してブール値を確保
      return metrics.map(metric => {
        console.log('カスタムmetric処理前:', metric);
        // is_higher_betterとisHigherBetterの両方をチェック
        const isHigherBetterValue = 
          metric.is_higher_better !== undefined ? Boolean(metric.is_higher_better) : 
          metric.isHigherBetter !== undefined ? Boolean(metric.isHigherBetter) : 
          true; // デフォルト値
        
        console.log(`カスタム ${metric.name}: is_higher_better=${metric.is_higher_better}, isHigherBetter=${metric.isHigherBetter}, 変換後=${isHigherBetterValue}`);
        
        return {
          ...metric,
          isHigherBetter: isHigherBetterValue
        };
      });
    } catch (error) {
      console.error('カスタム評価指標の取得に失敗しました:', error);
      throw error;
    }
  },
  
  // 評価指標一覧の取得（カスタムメトリクスのみ）
  getMetrics: async (): Promise<Metric[]> => {
    // カスタムメトリクスのみを返す
    return metricsApi.getCustomMetrics();
  },

  // 利用可能な評価指標タイプの取得
  getMetricTypes: async (): Promise<MetricTypeInfo[]> => {
    const response = await apiClient.get<{metrics: MetricTypeInfo[]}>('/api/v1/metrics/available');
    
    // 応答データの型変換を確実に行う
    const metricTypes = response.metrics || [];
    
    // データを適切に処理してブール値を確保
    return metricTypes.map(metricType => {
      console.log('メトリクスタイプ処理前:', metricType);
      // is_higher_betterの値をチェック
      const isHigherBetterValue = 
        metricType.is_higher_better !== undefined ? Boolean(metricType.is_higher_better) : true;
      
      console.log(`タイプ ${metricType.name}: is_higher_better=${metricType.is_higher_better}, 変換後=${isHigherBetterValue}`);
      
      return {
        ...metricType,
        is_higher_better: isHigherBetterValue
      };
    });
  },

  // 特定の評価指標の取得
  getMetric: async (id: string): Promise<Metric> => {
    const metric = await apiClient.get<Metric>(`/api/v1/metrics/${id}`);
    
    console.log('個別metric処理前:', metric);
    
    // is_higher_betterとisHigherBetterの両方をチェック
    const isHigherBetterValue = 
      metric.is_higher_better !== undefined ? Boolean(metric.is_higher_better) : 
      metric.isHigherBetter !== undefined ? Boolean(metric.isHigherBetter) : 
      true; // デフォルト値
    
    console.log(`個別 ${metric.name}: is_higher_better=${metric.is_higher_better}, isHigherBetter=${metric.isHigherBetter}, 変換後=${isHigherBetterValue}`);
    
    // データを適切に処理してブール値を確保
    return {
      ...metric,
      isHigherBetter: isHigherBetterValue
    };
  },

  // カスタム評価指標を削除
  deleteMetric: async (metricName: string): Promise<{message: string, name: string, path?: string}> => {
    return apiClient.delete<{message: string, name: string, path?: string}>(`/api/v1/metrics/${metricName}`);
  },

  // リーダーボードデータの取得
  getLeaderboard: async (filters?: LeaderboardFilterOptions): Promise<LeaderboardEntry[]> => {
    return apiClient.get<LeaderboardEntry[]>('/api/v1/evaluations/leaderboard', { params: filters });
  },

  // 推論に評価指標を適用
  applyMetricsToInference: async (inferenceId: string, metricIds: string[]): Promise<void> => {
    return apiClient.post<void>(`/api/v1/inferences/${inferenceId}/metrics`, { metricIds });
  },

  // リーダーボードデータのエクスポート（CSVファイル）
  exportLeaderboard: async (filters?: LeaderboardFilterOptions): Promise<Blob> => {
    return apiClient.getBlob('/api/v1/evaluations/leaderboard/export', { params: filters });
  },
};
