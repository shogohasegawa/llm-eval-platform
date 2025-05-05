import { apiClient } from './client';
import { EvaluationRequest, EvaluationResponse } from '../types/inference';

/**
 * 評価API
 * バックエンドの/api/evaluationsエンドポイントと連携
 */
export const evaluationApi = {
  // 評価実行API
  runEvaluation: async (request: EvaluationRequest): Promise<EvaluationResponse> => {
    console.log('Sending evaluation request:', request);
    return apiClient.post<EvaluationResponse>('/api/v1/evaluations/run', request);
  },
};
