import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { metricsApi } from '../api/metrics';
import { Metric, MetricFormData, LeaderboardEntry, LeaderboardFilterOptions, MetricTypeInfo } from '../types/metrics';

/**
 * 評価指標関連のカスタムフック
 */

// 評価指標一覧を取得するフック
export const useMetrics = () => {
  return useQuery<Metric[], Error>({
    queryKey: ['metrics'],
    queryFn: async () => {
      try {
        const result = await metricsApi.getMetrics();
        console.log('Metrics API response:', result);
        return result;
      } catch (error) {
        console.error('Metrics API error:', error);
        throw error;
      }
    },
  });
};

// 利用可能なメトリックタイプを取得するフック
export const useMetricTypes = () => {
  return useQuery<MetricTypeInfo[], Error>({
    queryKey: ['metricTypes'],
    queryFn: async () => {
      try {
        const result = await metricsApi.getMetricTypes();
        console.log('Metric Types API response:', result);
        return result;
      } catch (error) {
        console.error('Metric Types API error:', error);
        throw error;
      }
    },
  });
};

// 特定の評価指標を取得するフック
export const useMetric = (id: string) => {
  return useQuery<Metric, Error>({
    queryKey: ['metrics', id],
    queryFn: () => metricsApi.getMetric(id),
    enabled: !!id, // idが存在する場合のみクエリを実行
  });
};

// 評価指標を作成するフック
export const useCreateMetric = () => {
  const queryClient = useQueryClient();
  
  return useMutation<Metric, Error, MetricFormData>({
    mutationFn: async (data) => {
      console.log('Creating metric with data:', data);
      console.log('isHigherBetter value:', data.isHigherBetter);
      
      try {
        const result = await metricsApi.createMetric(data);
        console.log('Create metric result:', result);
        console.log('Result isHigherBetter:', result.isHigherBetter);
        return result;
      } catch (error) {
        console.error('Create metric error:', error);
        throw error;
      }
    },
    onSuccess: () => {
      // 成功時に評価指標一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
    },
  });
};

// 評価指標を更新するフック
export const useUpdateMetric = (id: string) => {
  const queryClient = useQueryClient();
  
  return useMutation<Metric, Error, MetricFormData>({
    mutationFn: (data) => metricsApi.updateMetric(id, data),
    onSuccess: () => {
      // 成功時に評価指標一覧と特定の評価指標を再取得
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
      queryClient.invalidateQueries({ queryKey: ['metrics', id] });
    },
  });
};

// 評価指標を削除するフック
export const useDeleteMetric = () => {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string>({
    mutationFn: (id) => metricsApi.deleteMetric(id),
    onSuccess: () => {
      // 成功時に評価指標一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
    },
  });
};

// リーダーボードデータを取得するフック
export const useLeaderboard = (filters?: LeaderboardFilterOptions) => {
  return useQuery<LeaderboardEntry[], Error>({
    queryKey: ['leaderboard', filters],
    queryFn: () => metricsApi.getLeaderboard(filters),
  });
};

// 推論に評価指標を適用するフック
export const useApplyMetricsToInference = (inferenceId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string[]>({
    mutationFn: (metricIds) => metricsApi.applyMetricsToInference(inferenceId, metricIds),
    onSuccess: () => {
      // 成功時に推論データとリーダーボードデータを再取得
      queryClient.invalidateQueries({ queryKey: ['inferences', inferenceId] });
      queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
    },
  });
};

// リーダーボードデータをエクスポートするフック
export const useExportLeaderboard = () => {
  return useMutation<Blob, Error, LeaderboardFilterOptions | undefined>({
    mutationFn: (filters) => metricsApi.exportLeaderboard(filters),
  });
};
