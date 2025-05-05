import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { providersApi } from '../api/providers';
import { Provider, ProviderFormData, Model, ModelFormData } from '../types/provider';

/**
 * LLMプロバイダとモデル関連のカスタムフック
 */

// プロバイダ一覧を取得するフック
export const useProviders = () => {
  return useQuery<Provider[], Error>({
    queryKey: ['providers'],
    queryFn: () => providersApi.getProviders(),
  });
};

// 特定のプロバイダを取得するフック
export const useProvider = (id: string) => {
  return useQuery<Provider, Error>({
    queryKey: ['providers', id],
    queryFn: () => providersApi.getProvider(id),
    enabled: !!id, // idが存在する場合のみクエリを実行
  });
};

// プロバイダを作成するフック
export const useCreateProvider = () => {
  const queryClient = useQueryClient();
  
  return useMutation<Provider, Error, ProviderFormData>({
    mutationFn: (data) => providersApi.createProvider(data),
    onSuccess: () => {
      // 成功時にプロバイダ一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });
};

// プロバイダを更新するフック
export const useUpdateProvider = (id: string) => {
  const queryClient = useQueryClient();
  
  return useMutation<Provider, Error, ProviderFormData>({
    mutationFn: (data) => providersApi.updateProvider(id, data),
    onSuccess: () => {
      // 成功時にプロバイダ一覧と特定のプロバイダを再取得
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      queryClient.invalidateQueries({ queryKey: ['providers', id] });
    },
  });
};

// プロバイダを削除するフック
export const useDeleteProvider = () => {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string>({
    mutationFn: (id) => providersApi.deleteProvider(id),
    onSuccess: () => {
      // 成功時にプロバイダ一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      // モデル一覧も再取得
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });
};

// モデル一覧を取得するフック
export const useModels = () => {
  return useQuery<Model[], Error>({
    queryKey: ['models'],
    queryFn: async () => {
      try {
        const result = await providersApi.getAllModels();
        console.log('Models API response:', result);
        
        // レスポンスがないか不適切な形式の場合のバリデーション
        if (!result || !Array.isArray(result)) {
          console.warn('Models API returned invalid format:', result);
          return [];
        }
        
        // モデルIDの検証とロギング
        result.forEach((model, index) => {
          if (!model.id) {
            console.warn(`Model at index ${index} has no ID:`, model);
          }
        });
        
        return result;
      } catch (error) {
        console.error('Models API error:', error);
        throw error;
      }
    },
    // 再試行設定
    retry: 2,
    retryDelay: 1000,
    // キャッシュとステール設定
    staleTime: 30000, // 30秒間はキャッシュを使用
    refetchOnWindowFocus: true,
  });
};

// 特定のモデルを取得するフック
export const useModel = (id: string) => {
  return useQuery<Model, Error>({
    queryKey: ['models', id],
    queryFn: () => providersApi.getModel(id),
    enabled: !!id,
  });
};

// プロバイダのモデル一覧を取得するフック
export const useProviderModels = (providerId: string) => {
  return useQuery<Model[], Error>({
    queryKey: ['providers', providerId, 'models'],
    queryFn: () => providersApi.getProviderModels(providerId),
    enabled: !!providerId, // providerIdが存在する場合のみクエリを実行
  });
};

// モデルを作成するフック
export const useCreateModel = () => {
  const queryClient = useQueryClient();
  
  return useMutation<Model, Error, ModelFormData>({
    mutationFn: (data) => providersApi.createModel(data),
    onSuccess: (data) => {
      // 成功時にモデル一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['models'] });
      // プロバイダのモデル一覧も再取得
      queryClient.invalidateQueries({ queryKey: ['providers', data.providerId, 'models'] });
    },
  });
};

// モデルを更新するフック
export const useUpdateModel = (modelId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation<Model, Error, ModelFormData>({
    mutationFn: (data) => providersApi.updateModel(modelId, data),
    onSuccess: (data) => {
      // 成功時にモデル一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['models'] });
      // 特定のモデルも再取得
      queryClient.invalidateQueries({ queryKey: ['models', modelId] });
      // プロバイダのモデル一覧も再取得
      queryClient.invalidateQueries({ queryKey: ['providers', data.providerId, 'models'] });
    },
  });
};

// モデルを削除するフック
export const useDeleteModel = () => {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, {modelId: string, providerId: string}>({
    mutationFn: ({modelId}) => providersApi.deleteModel(modelId),
    onSuccess: (_, variables) => {
      // 成功時にモデル一覧を再取得
      queryClient.invalidateQueries({ queryKey: ['models'] });
      // プロバイダのモデル一覧も再取得
      queryClient.invalidateQueries({ queryKey: ['providers', variables.providerId, 'models'] });
    },
  });
};
