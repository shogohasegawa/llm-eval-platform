import { apiClient } from './client';
import { Inference, InferenceFormData, InferenceResult, InferenceFilterOptions, EvaluationRequest, ModelConfig } from '../types/inference';
import { Model } from '../types/provider';

/**
 * 推論API
 */
export const inferencesApi = {
  // 推論一覧の取得
  getInferences: async (filters?: InferenceFilterOptions): Promise<Inference[]> => {
    return apiClient.get<Inference[]>('/inferences', { params: filters });
  },

  // 特定の推論の取得
  getInference: async (id: string): Promise<Inference> => {
    return apiClient.get<Inference>(`/inferences/${id}`);
  },

  // 推論の作成
  createInference: async (data: InferenceFormData): Promise<Inference> => {
    console.log('Creating inference with data:', data);
    
    // データセットIDが空かundefinedの場合は、エラーを表示して処理を中止
    if (!data.datasetId || data.datasetId === 'undefined') {
      console.error('データセットIDが未選択です');
      throw new Error('データセットを選択してください');
    }
    
    // プロバイダIDが空かundefinedの場合は、エラーを表示して処理を中止
    if (!data.providerId || data.providerId === 'undefined') {
      console.error('プロバイダIDが未選択です');
      throw new Error('プロバイダを選択してください');
    }
    
    // モデルIDが空かundefinedの場合は、エラーを表示して処理を中止
    if (!data.modelId || data.modelId === 'undefined') {
      console.error('モデルIDが未選択です');
      throw new Error('モデルを選択してください');
    }
    
    // データセットIDをファイル名として使用（.jsonを除去）
    // "test/example.json" -> "example"
    const datasetName = data.datasetId.split('/').pop()?.replace('.json', '') || data.datasetId;
    console.log('Using dataset name:', datasetName);
    
    try {
      // モデル設定を構築
      const modelConfig: ModelConfig = {
        provider: "ollama", // プロバイダタイプ（固定値としてollamaを使用）
        model_name: "gpt4", // モデル名（固定値としてgpt4を使用）
        max_tokens: data.maxTokens || 512,
        temperature: data.temperature || 0.7,
        top_p: data.topP || 1.0
      };
      
      // 評価リクエストを構築 
      const evaluationRequest: EvaluationRequest = {
        datasets: [datasetName], // ファイル名のみを使用
        num_samples: data.numSamples || 100,
        n_shots: [data.nShots || 0],
        model: modelConfig
      };
      
      console.log('Sending evaluation request:', evaluationRequest);
      
      // 評価APIを呼び出す
      const evalResponse = await apiClient.post('/api/evaluation/run', evaluationRequest);
      console.log('Evaluation response:', evalResponse);
      
      // 仮のInferenceオブジェクトを作成
      const inference: Inference = {
        id: `temp-${Date.now()}`,
        name: data.name,
        description: data.description || '',
        datasetId: data.datasetId,
        providerId: data.providerId,
        modelId: data.modelId,
        status: 'completed',
        progress: 100,
        results: [],
        metrics: evalResponse.metrics,
        createdAt: new Date(),
        updatedAt: new Date(),
        completedAt: new Date()
      };
      
      return inference;
    } catch (error) {
      console.error('Error creating inference:', error);
      throw error;
    }
  },

  // 推論の更新
  updateInference: async (id: string, data: Partial<InferenceFormData>): Promise<Inference> => {
    return apiClient.put<Inference>(`/inferences/${id}`, data);
  },

  // 推論の削除
  deleteInference: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/inferences/${id}`);
  },

  // 推論の実行
  runInference: async (id: string): Promise<Inference> => {
    return apiClient.post<Inference>(`/inferences/${id}/run`);
  },

  // 推論の停止
  stopInference: async (id: string): Promise<Inference> => {
    return apiClient.post<Inference>(`/inferences/${id}/stop`);
  },

  // 推論結果の取得
  getInferenceResults: async (inferenceId: string): Promise<InferenceResult[]> => {
    return apiClient.get<InferenceResult[]>(`/inferences/${inferenceId}/results`);
  },

  // 特定の推論結果の取得
  getInferenceResult: async (inferenceId: string, resultId: string): Promise<InferenceResult> => {
    return apiClient.get<InferenceResult>(`/inferences/${inferenceId}/results/${resultId}`);
  },

  // 推論結果のエクスポート（CSVファイル）
  exportInferenceResults: async (id: string): Promise<Blob> => {
    return apiClient.get<Blob>(`/inferences/${id}/export`, {
      responseType: 'blob',
    });
  },

  // 評価APIを直接呼び出す（バックエンドと連携時に使用）
  runEvaluation: async (evaluationRequest: EvaluationRequest): Promise<any> => {
    return apiClient.post('/api/evaluation/run', evaluationRequest);
  }
};
