import { apiClient } from './client';
import { Inference, InferenceFormData, InferenceResult, InferenceFilterOptions, EvaluationRequest, ModelConfig } from '../types/inference';
import { Model } from '../types/provider';

/**
 * 推論API
 */
export const inferencesApi = {
  // 推論一覧の取得
  getInferences: async (filters?: InferenceFilterOptions): Promise<Inference[]> => {
    return apiClient.get<Inference[]>('/api/inferences', { params: filters });
  },

  // 特定の推論の取得
  getInference: async (id: string): Promise<Inference> => {
    return apiClient.get<Inference>(`/api/inferences/${id}`);
  },

  // 推論の作成
  createInference: async (data: InferenceFormData): Promise<Inference> => {
    console.log('Creating inference with data:', data);
    
    // バリデーション
    if (!data.datasetId || data.datasetId === 'undefined') {
      console.error('データセットIDが未選択です');
      throw new Error('データセットを選択してください');
    }
    
    if (!data.providerId || data.providerId === 'undefined') {
      console.error('プロバイダIDが未選択です');
      throw new Error('プロバイダを選択してください');
    }
    
    if (!data.modelId || data.modelId === 'undefined') {
      console.error('モデルIDが未選択です');
      throw new Error('モデルを選択してください');
    }
    
    try {
      // バックエンドAPIを呼び出してデータ処理を任せる
      const response = await apiClient.post<Inference>('/api/inferences', data);
      return response;
    } catch (error) {
      console.error('Error creating inference:', error);
      throw error;
    }
  },

  // 推論の更新
  updateInference: async (id: string, data: Partial<InferenceFormData>): Promise<Inference> => {
    return apiClient.put<Inference>(`/api/inferences/${id}`, data);
  },

  // 推論の削除
  deleteInference: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/api/inferences/${id}`);
  },

  // 推論の実行
  runInference: async (id: string): Promise<Inference> => {
    return apiClient.post<Inference>(`/api/inferences/${id}/run`);
  },

  // 推論の停止
  stopInference: async (id: string): Promise<Inference> => {
    return apiClient.post<Inference>(`/api/inferences/${id}/stop`);
  },

  // 推論結果の取得
  getInferenceResults: async (inferenceId: string): Promise<InferenceResult[]> => {
    return apiClient.get<InferenceResult[]>(`/api/inferences/${inferenceId}/results`);
  },

  // 特定の推論結果の取得
  getInferenceResult: async (inferenceId: string, resultId: string): Promise<InferenceResult> => {
    return apiClient.get<InferenceResult>(`/api/inferences/${inferenceId}/results/${resultId}`);
  },

  // 推論結果のエクスポート（CSVファイル）
  exportInferenceResults: async (id: string): Promise<Blob> => {
    return apiClient.get<Blob>(`/api/inferences/${id}/export`, {
      responseType: 'blob',
    });
  },

  // 評価APIを直接呼び出す（特殊ケース用）
  runEvaluation: async (evaluationRequest: EvaluationRequest): Promise<any> => {
    return apiClient.post('/api/evaluations/run', evaluationRequest);
  }
};
