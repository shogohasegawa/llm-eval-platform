import { apiClient } from './client';
import { Metric, MetricFormData, LeaderboardEntry, LeaderboardFilterOptions, MetricTypeInfo } from '../types/metrics';

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

  // 評価指標の作成
  createMetric: async (data: MetricFormData): Promise<Metric> => {
    // isHigherBetterを明示的にブール値として処理
    const isHigherBetterValue = !!data.isHigherBetter;
    
    console.log('メトリクス作成前のデータ:', data);
    console.log(`isHigherBetter 変換: ${data.isHigherBetter} (${typeof data.isHigherBetter}) -> ${isHigherBetterValue} (${typeof isHigherBetterValue})`);
    
    // 送信データを用意（明示的にブール値を設定）
    const sendData = {
      ...data,
      isHigherBetter: isHigherBetterValue
    };
    
    console.log('メトリクス作成送信データ:', sendData);
    
    return apiClient.post<Metric>('/api/v1/metrics', sendData);
  },

  // 評価指標の更新
  updateMetric: async (id: string, data: MetricFormData): Promise<Metric> => {
    // isHigherBetterを明示的にブール値として処理
    const isHigherBetterValue = !!data.isHigherBetter;
    
    console.log('メトリクス更新前のデータ:', data);
    console.log(`isHigherBetter 変換: ${data.isHigherBetter} (${typeof data.isHigherBetter}) -> ${isHigherBetterValue} (${typeof isHigherBetterValue})`);
    
    // 送信データを用意（明示的にブール値を設定）
    const sendData = {
      ...data,
      isHigherBetter: isHigherBetterValue
    };
    
    console.log('メトリクス更新送信データ:', sendData);
    
    return apiClient.put<Metric>(`/api/v1/metrics/${id}`, sendData);
  },

  // 評価指標の削除
  deleteMetric: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/metrics/${id}`);
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
