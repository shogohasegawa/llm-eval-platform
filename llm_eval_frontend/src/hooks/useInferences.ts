import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inferencesApi } from '../api/inferences';
import { Inference, InferenceFormData, InferenceResult, InferenceFilterOptions } from '../types/inference';

/**
 * 推論関連のカスタムフック
 */

// 推論一覧を取得するフック
export const useInferences = (filters?: InferenceFilterOptions) => {
  return useQuery<Inference[], Error>({
    queryKey: ['inferences', filters],
    queryFn: () => inferencesApi.getInferences(filters),
  });
};

// 特定の推論を取得するフック
export const useInference = (id: string) => {
  return useQuery<Inference, Error>({
    queryKey: ['inferences', id],
    queryFn: () => inferencesApi.getInference(id),
    enabled: !!id, // idが存在する場合のみクエリを実行
  });
};

// 推論を作成するフック
export const useCreateInference = () => {
  const queryClient = useQueryClient();
  
  return useMutation<Inference, Error, InferenceFormData>({
    mutationFn: (data) => inferencesApi.createInference(data),
    onSuccess: () => {
      // 成功時に推論一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['inferences'] });
    },
  });
};

// 推論を更新するフック
export const useUpdateInference = (id: string) => {
  const queryClient = useQueryClient();
  
  return useMutation<Inference, Error, Partial<InferenceFormData>>({
    mutationFn: (data) => inferencesApi.updateInference(id, data),
    onSuccess: () => {
      // 成功時に推論一覧と特定の推論を再取得
      queryClient.invalidateQueries({ queryKey: ['inferences'] });
      queryClient.invalidateQueries({ queryKey: ['inferences', id] });
    },
  });
};

// 推論を削除するフック
export const useDeleteInference = () => {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string>({
    mutationFn: (id) => inferencesApi.deleteInference(id),
    onSuccess: () => {
      // 成功時に推論一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['inferences'] });
    },
  });
};

// 推論を実行するフック
export const useRunInference = (id: string) => {
  const queryClient = useQueryClient();
  
  return useMutation<Inference, Error, void>({
    mutationFn: () => inferencesApi.runInference(id),
    onSuccess: () => {
      // 成功時に特定の推論を再取得
      queryClient.invalidateQueries({ queryKey: ['inferences', id] });
    },
  });
};

// 推論を停止するフック
export const useStopInference = (id: string) => {
  const queryClient = useQueryClient();
  
  return useMutation<Inference, Error, void>({
    mutationFn: () => inferencesApi.stopInference(id),
    onSuccess: () => {
      // 成功時に特定の推論を再取得
      queryClient.invalidateQueries({ queryKey: ['inferences', id] });
    },
  });
};

// 推論結果一覧を取得するフック
export const useInferenceResults = (inferenceId: string) => {
  return useQuery<InferenceResult[], Error>({
    queryKey: ['inferences', inferenceId, 'results'],
    queryFn: () => inferencesApi.getInferenceResults(inferenceId),
    enabled: !!inferenceId, // inferenceIdが存在する場合のみクエリを実行
  });
};

// 特定の推論結果を取得するフック
export const useInferenceResult = (inferenceId: string, resultId: string) => {
  return useQuery<InferenceResult, Error>({
    queryKey: ['inferences', inferenceId, 'results', resultId],
    queryFn: () => inferencesApi.getInferenceResult(inferenceId, resultId),
    enabled: !!inferenceId && !!resultId, // 両方のIDが存在する場合のみクエリを実行
  });
};

// 推論結果をエクスポートするフック
export const useExportInferenceResults = (inferenceId: string) => {
  return useMutation<Blob, Error, void>({
    mutationFn: () => inferencesApi.exportInferenceResults(inferenceId),
  });
};
