import { apiClient } from './client';
import { Inference, InferenceFormData, InferenceResult, InferenceFilterOptions, EvaluationRequest, ModelConfig } from '../types/inference';
import { Model } from '../types/provider';

/**
 * 推論API
 */
export const inferencesApi = {
  // 推論一覧の取得
  getInferences: async (filters?: InferenceFilterOptions): Promise<Inference[]> => {
    const response = await apiClient.get<any[] | {inferences: any[]}>('/api/v1/inferences', { params: filters });
    
    // データの取得
    let rawInferences: any[] = [];
    if (Array.isArray(response)) {
      console.log('直接配列形式の推論リストを受信しました', response.length);
      rawInferences = response;
    } else if (response && typeof response === 'object' && 'inferences' in response) {
      console.log('オブジェクトでラップされた推論リストを受信しました', response.inferences?.length);
      rawInferences = response.inferences || [];
    } else {
      console.warn('不明な形式の推論リストレスポンス:', response);
      rawInferences = Array.isArray(response) ? response : [];
    }
    
    // snake_caseからcamelCaseへの変換とデータ整形
    return rawInferences.map(item => {
      const inference: Inference = {
        id: item.id,
        name: item.name,
        description: item.description || '',
        datasetId: item.dataset_id || item.datasetId,
        providerId: item.provider_id || item.providerId,
        modelId: item.model_id || item.modelId,
        status: item.status,
        progress: item.progress,
        results: item.results || [],
        metrics: item.metrics,
        // 日付の変換 - サーバー側のタイムゾーン設定に依存せずに文字列として保持
        createdAt: item.created_at || item.createdAt || new Date().toISOString(),
        updatedAt: item.updated_at || item.updatedAt || new Date().toISOString(),
        completedAt: item.completed_at || item.completedAt,
        error: item.error
      };
      return inference;
    });
  },

  // 特定の推論の取得
  getInference: async (id: string): Promise<Inference> => {
    const item = await apiClient.get<any>(`/api/v1/inferences/${id}`);
    
    // snake_caseからcamelCaseへの変換とデータ整形
    const inference: Inference = {
      id: item.id,
      name: item.name,
      description: item.description || '',
      datasetId: item.dataset_id || item.datasetId,
      providerId: item.provider_id || item.providerId,
      modelId: item.model_id || item.modelId,
      status: item.status,
      progress: item.progress,
      results: item.results || [],
      metrics: item.metrics,
      // 日付の変換 - サーバー側のタイムゾーン設定に依存せずに文字列として保持
      createdAt: item.created_at || item.createdAt || new Date().toISOString(),
      updatedAt: item.updated_at || item.updatedAt || new Date().toISOString(),
      completedAt: item.completed_at || item.completedAt,
      error: item.error
    };
    
    return inference;
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
      // ユーザー指定のサンプル数を尊重する
      const processedData = {
        ...data,
        // ユーザーが指定したサンプル数を使用（指定がなければデフォルト100）
        numSamples: data.numSamples || 100,
        // バックエンドAPI期待する形式にフィールド名を変換（スネークケース）
        dataset_id: data.datasetId,
        provider_id: data.providerId,
        model_id: data.modelId,
        max_tokens: data.maxTokens || 512,
        top_p: data.topP || 1.0,
        n_shots: data.nShots || 0,
        num_samples: data.numSamples || 100, // スネークケース版も設定
        temperature: data.temperature || 0.7,
        // datasetId、providerId、modelIdプロパティを削除（重複を防ぐため）
        datasetId: undefined,
        providerId: undefined,
        modelId: undefined,
        maxTokens: undefined,
        topP: undefined,
        nShots: undefined
      };
      
      console.log('Processed inference data:', processedData);
      
      // バックエンドAPIを呼び出してデータ処理を任せる
      const response = await apiClient.post<Inference>('/api/v1/inferences', processedData);
      console.log('Inference creation response:', response);
      
      // レスポンスが直接Inferenceオブジェクトではなく、ラップされている可能性があるのでチェック
      if (response && typeof response === 'object') {
        if ('inference' in response) {
          return response.inference as Inference;
        }
      }
      
      return response;
    } catch (error) {
      console.error('Error creating inference:', error);
      throw error;
    }
  },

  // 推論の更新
  updateInference: async (id: string, data: Partial<InferenceFormData>): Promise<Inference> => {
    return apiClient.put<Inference>(`/api/v1/inferences/${id}`, data);
  },

  // 推論の削除
  deleteInference: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/inferences/${id}`);
  },

  // 推論の実行
  runInference: async (id: string): Promise<Inference> => {
    return apiClient.post<Inference>(`/api/v1/inferences/${id}/run`);
  },

  // 推論の停止
  stopInference: async (id: string): Promise<Inference> => {
    return apiClient.post<Inference>(`/api/v1/inferences/${id}/stop`);
  },

  // 推論結果の取得
  getInferenceResults: async (inferenceId: string): Promise<InferenceResult[]> => {
    const response = await apiClient.get<{results: InferenceResult[]}>(`/api/v1/inferences/${inferenceId}/results`);
    return response.results || [];
  },

  // 特定の推論結果の取得
  getInferenceResult: async (inferenceId: string, resultId: string): Promise<InferenceResult> => {
    return apiClient.get<InferenceResult>(`/api/v1/inferences/${inferenceId}/results/${resultId}`);
  },

  // 推論結果のエクスポート（CSVファイル）
  exportInferenceResults: async (id: string): Promise<Blob> => {
    return apiClient.get<Blob>(`/api/v1/inferences/${id}/export`, {
      responseType: 'blob',
    });
  },
  
  // 推論の詳細情報を取得
  getInferenceDetail: async (id: string): Promise<any> => {
    return apiClient.get<any>(`/api/v1/inferences/${id}/detail`);
  },

  // 評価APIを直接呼び出す（特殊ケース用）
  runEvaluation: async (evaluationRequest: EvaluationRequest): Promise<any> => {
    return apiClient.post('/api/v1/evaluations/run', evaluationRequest);
  }
};
