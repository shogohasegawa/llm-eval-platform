import { useMutation } from '@tanstack/react-query';
import { evaluationApi } from '../api/evaluation';
import { EvaluationRequest, EvaluationResponse } from '../types/inference';

/**
 * 評価実行関連のカスタムフック
 */
export const useRunEvaluation = () => {
  return useMutation<EvaluationResponse, Error, EvaluationRequest>({
    mutationFn: (request) => evaluationApi.runEvaluation(request),
  });
};
