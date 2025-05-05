import { apiClient } from './client';
import { Provider, ProviderFormData, Model, ModelFormData } from '../types/provider';

/**
 * LLMプロバイダとモデルAPI
 * バックエンドの/api/providersと/api/modelsエンドポイントと連携
 */
export const providersApi = {
  // プロバイダ一覧の取得
  getProviders: async (): Promise<Provider[]> => {
    return apiClient.get<Provider[]>('/api/providers');
  },

  // 特定のプロバイダの取得
  getProvider: async (id: string): Promise<Provider> => {
    return apiClient.get<Provider>(`/api/providers/${id}`);
  },

  // プロバイダの作成
  createProvider: async (data: ProviderFormData): Promise<Provider> => {
    // プロバイダ名に基づいて適切なタイプを設定
    let providerType = 'custom'; // デフォルトはcustom

    // 大文字小文字を区別せずに名前を比較
    const name = data.name.toLowerCase().trim();
    
    if (name === 'ollama') {
      providerType = 'ollama';
    } else if (name === 'openai') {
      providerType = 'openai';
    } else if (name === 'anthropic') {
      providerType = 'anthropic';
    } else if (name.includes('claude')) {
      providerType = 'anthropic';
    } else if (name.includes('gpt')) {
      providerType = 'openai';
    }

    // バックエンド要件に合わせて type フィールドを追加
    const dataWithType = {
      ...data,
      type: providerType
    };
    
    console.log(`Creating provider with type: ${providerType} for name: ${data.name}`);
    return apiClient.post<Provider>('/api/providers', dataWithType);
  },

  // プロバイダの更新
  updateProvider: async (id: string, data: ProviderFormData): Promise<Provider> => {
    // プロバイダ名に基づいて適切なタイプを設定
    let typeToUpdate = undefined;

    // 名前が更新されていれば、その名前に応じたタイプを設定
    if (data.name) {
      const name = data.name.toLowerCase().trim();
      
      if (name === 'ollama') {
        typeToUpdate = 'ollama';
      } else if (name === 'openai') {
        typeToUpdate = 'openai';
      } else if (name === 'anthropic') {
        typeToUpdate = 'anthropic';
      } else if (name.includes('claude')) {
        typeToUpdate = 'anthropic';
      } else if (name.includes('gpt')) {
        typeToUpdate = 'openai';
      } else {
        typeToUpdate = 'custom';
      }
    }

    // バックエンド要件に合わせて type フィールドを追加
    const dataWithType = {
      ...data,
      type: typeToUpdate // 名前が更新されていれば自動的にタイプも更新
    };
    
    if (typeToUpdate) {
      console.log(`Updating provider with type: ${typeToUpdate} for name: ${data.name}`);
    }
    
    return apiClient.put<Provider>(`/api/providers/${id}`, dataWithType);
  },

  // プロバイダの削除
  deleteProvider: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/api/providers/${id}`);
  },

  // すべてのモデル一覧の取得
  getAllModels: async (): Promise<Model[]> => {
    return apiClient.get<Model[]>('/api/models');
  },

  // 特定のモデルの取得
  getModel: async (id: string): Promise<Model> => {
    return apiClient.get<Model>(`/api/models/${id}`);
  },

  // プロバイダのモデル一覧の取得
  getProviderModels: async (providerId: string): Promise<Model[]> => {
    return apiClient.get<Model[]>(`/api/models/by-provider/${providerId}`);
  },

  // モデルの作成
  createModel: async (data: ModelFormData): Promise<Model> => {
    // データの前処理: 空文字列のエンドポイントとAPIキーをundefinedに変換
    const processedData = {
      ...data,
      endpoint: data.endpoint?.trim() || undefined,
      apiKey: data.apiKey?.trim() || undefined
    };
    
    console.log(`Creating model:`, processedData);
    try {
      const result = await apiClient.post<Model>('/api/models', processedData);
      console.log('API response:', result);
      return result;
    } catch (error) {
      console.error('API error creating model:', error);
      throw error;
    }
  },

  // モデルの更新
  updateModel: async (modelId: string, data: ModelFormData): Promise<Model> => {
    // データの前処理: 空文字列のエンドポイントとAPIキーをundefinedに変換
    const processedData = {
      ...data,
      endpoint: data.endpoint?.trim() || undefined,
      apiKey: data.apiKey?.trim() || undefined
    };
    return apiClient.put<Model>(`/api/models/${modelId}`, processedData);
  },

  // モデルの削除
  deleteModel: async (modelId: string): Promise<void> => {
    return apiClient.delete<void>(`/api/models/${modelId}`);
  }
};
