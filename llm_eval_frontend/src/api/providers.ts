import { apiClient } from './client';
import { Provider, ProviderFormData, Model, ModelFormData } from '../types/provider';

/**
 * LLMプロバイダとモデルAPI
 * バックエンドの/api/providersと/api/modelsエンドポイントと連携
 */
export const providersApi = {
  // プロバイダ一覧の取得
  getProviders: async (): Promise<Provider[]> => {
    try {
      const response = await apiClient.get<any>('/api/v1/providers');
      console.log('API Response - getProviders:', response);
      
      // レスポンスがArray型の場合
      if (Array.isArray(response)) {
        console.log('Providers response is array with length:', response.length);
        return response;
      }
      
      // レスポンスがオブジェクトでprovidersプロパティがある場合
      if (response && typeof response === 'object' && 'providers' in response && Array.isArray(response.providers)) {
        console.log('Providers response has providers property with length:', response.providers.length);
        return response.providers;
      }
      
      // データの中身がプロバイダの配列である可能性がある場合
      const possibleArrayProps = Object.keys(response).filter(key => 
        Array.isArray(response[key]) && 
        response[key].length > 0 && 
        typeof response[key][0] === 'object' &&
        'name' in response[key][0] &&
        ('type' in response[key][0] || 'id' in response[key][0])
      );
      
      if (possibleArrayProps.length > 0) {
        console.log(`Found potential providers array in property: ${possibleArrayProps[0]}`);
        return response[possibleArrayProps[0]];
      }
      
      console.log('Providers response is in unexpected format:', response);
      return [];
    } catch (error) {
      console.error('Error fetching providers:', error);
      return [];
    }
  },

  // 特定のプロバイダの取得
  getProvider: async (id: string): Promise<Provider> => {
    try {
      const response = await apiClient.get<any>(`/api/v1/providers/${id}`);
      console.log('API Response - getProvider:', response);
      
      // レスポンスがプロバイダオブジェクト自体の場合
      if (response && typeof response === 'object' && 'id' in response && 'name' in response) {
        return response as Provider;
      }
      
      // レスポンスが{provider: Provider}の形式の場合
      if (response && typeof response === 'object' && 'provider' in response) {
        return response.provider as Provider;
      }
      
      // その他の場合
      console.log('Provider response is in unexpected format:', response);
      throw new Error('プロバイダデータの取得に失敗しました');
    } catch (error) {
      console.error('Error fetching provider:', error);
      throw error;
    }
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
      type: providerType,
      // スネークケース版のフィールドも送信
      is_active: data.isActive,
      api_key: data.apiKey
    };
    
    console.log(`Creating provider with type: ${providerType} for name: ${data.name}`);
    
    try {
      const response = await apiClient.post<any>('/api/v1/providers', dataWithType);
      console.log('API create provider response:', response);
      
      // レスポンスがプロバイダオブジェクト自体の場合
      if (response && typeof response === 'object' && 
         ('id' in response || 'provider_id' in response) && 'name' in response) {
        return response as Provider;
      }
      
      // レスポンスが{provider: Provider}の形式の場合
      if (response && typeof response === 'object' && 'provider' in response) {
        return response.provider as Provider;
      }
      
      // レスポンスの形式が期待と異なる場合でも処理を試みる
      return {
        id: response.id || response.provider_id || '',
        name: data.name,
        type: providerType,
        endpoint: data.endpoint,
        apiKey: data.apiKey,
        isActive: data.isActive
      } as Provider;
    } catch (error) {
      console.error('API error creating provider:', error);
      throw error;
    }
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
      type: typeToUpdate, // 名前が更新されていれば自動的にタイプも更新
      // スネークケース版のフィールドも送信
      is_active: data.isActive,
      api_key: data.apiKey
    };
    
    if (typeToUpdate) {
      console.log(`Updating provider with type: ${typeToUpdate} for name: ${data.name}`);
    }
    
    try {
      const response = await apiClient.put<any>(`/api/v1/providers/${id}`, dataWithType);
      console.log('API update provider response:', response);
      
      // レスポンスがプロバイダオブジェクト自体の場合
      if (response && typeof response === 'object' && 
         ('id' in response || 'provider_id' in response) && 'name' in response) {
        return response as Provider;
      }
      
      // レスポンスが{provider: Provider}の形式の場合
      if (response && typeof response === 'object' && 'provider' in response) {
        return response.provider as Provider;
      }
      
      // レスポンスの形式が期待と異なる場合でも処理を試みる
      return {
        id,
        name: data.name,
        type: typeToUpdate || 'custom',
        endpoint: data.endpoint,
        apiKey: data.apiKey,
        isActive: data.isActive
      } as Provider;
    } catch (error) {
      console.error('API error updating provider:', error);
      throw error;
    }
  },

  // プロバイダの削除
  deleteProvider: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/providers/${id}`);
  },

  // すべてのモデル一覧の取得
  getAllModels: async (): Promise<Model[]> => {
    try {
      const response = await apiClient.get<any>('/api/v1/models');
      console.log('Raw models response:', response);
      
      // レスポンスがArray型の場合
      if (Array.isArray(response)) {
        console.log('Models response is an array with length:', response.length);
        return response;
      }
      
      // レスポンスがオブジェクトの場合、modelsプロパティを取得
      if (response && typeof response === 'object') {
        // 'models' プロパティがある場合
        if ('models' in response && Array.isArray(response.models)) {
          console.log('Models response has models property with length:', response.models.length);
          return response.models;
        }
        
        // データの中身がモデルの配列である可能性がある場合
        const possibleArrayProps = Object.keys(response).filter(key => 
          Array.isArray(response[key]) && 
          response[key].length > 0 && 
          typeof response[key][0] === 'object' &&
          'name' in response[key][0] &&
          'providerId' in response[key][0]
        );
        
        if (possibleArrayProps.length > 0) {
          console.log(`Found potential models array in property: ${possibleArrayProps[0]}`);
          return response[possibleArrayProps[0]];
        }
      }
      
      // それ以外の場合は空配列を返す
      console.log('Models response is in unexpected format:', response);
      return [];
    } catch (error) {
      console.error('Error fetching models:', error);
      return [];
    }
  },

  // 特定のモデルの取得
  getModel: async (id: string): Promise<Model> => {
    return apiClient.get<Model>(`/api/v1/models/${id}`);
  },

  // プロバイダのモデル一覧の取得
  getProviderModels: async (providerId: string): Promise<Model[]> => {
    try {
      const response = await apiClient.get<any>(`/api/v1/models/by-provider/${providerId}`);
      console.log('Provider models API response:', response);
      
      // レスポンスが直接配列の場合
      if (Array.isArray(response)) {
        return response;
      }
      
      // レスポンスがオブジェクトで'models'プロパティがある場合
      if (response && typeof response === 'object' && 'models' in response && Array.isArray(response.models)) {
        return response.models;
      }
      
      // レスポンスがオブジェクトで、その中に配列が含まれている可能性がある場合
      if (response && typeof response === 'object') {
        // オブジェクトのプロパティを調べる
        for (const key in response) {
          if (Array.isArray(response[key])) {
            return response[key];
          }
        }
      }
      
      console.warn('Unexpected API response format for provider models:', response);
      return [];
    } catch (error) {
      console.error('Error fetching provider models:', error);
      return [];
    }
  },

  // モデルの作成
  createModel: async (data: ModelFormData): Promise<Model> => {
    // データの前処理: 空文字列のエンドポイントとAPIキーをundefinedに変換
    const processedData = {
      ...data,
      endpoint: data.endpoint?.trim() || undefined,
      apiKey: data.apiKey?.trim() || undefined,
      // バックエンドが期待する可能性のあるスネークケースのフィールドも追加
      provider_id: data.providerId
    };
    
    console.log(`Creating model with data:`, processedData);
    try {
      const response = await apiClient.post<any>('/api/v1/models', processedData);
      console.log('API create model response:', response);
      
      // さまざまな形式のレスポンスを処理
      if (response) {
        // レスポンスがモデルオブジェクト自体である場合
        if (response.id && response.name && response.providerId) {
          console.log('Response is a model object');
          return response as Model;
        }
        
        // レスポンスが{model: Model}の形式である場合
        if (typeof response === 'object' && 'model' in response && response.model) {
          console.log('Response contains model property');
          return response.model as Model;
        }
        
        // レスポンスが他のオブジェクト内にモデル情報を含む場合
        const modelProps = ['id', 'name', 'providerId', 'displayName'];
        for (const key of Object.keys(response)) {
          const value = response[key];
          if (typeof value === 'object' && value !== null && 
              modelProps.every(prop => prop in value || prop.toLowerCase() in value)) {
            console.log(`Found model in property: ${key}`);
            return value as Model;
          }
        }
      }
      
      // レスポンスの形式が期待と異なる場合でも処理を試みる
      console.log('Attempting to construct model from response:', response);
      return {
        id: response.id || response.model_id || '',
        providerId: data.providerId,
        name: data.name,
        displayName: data.displayName || data.name,
        description: data.description,
        isActive: data.isActive
      } as Model;
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
      apiKey: data.apiKey?.trim() || undefined,
      // バックエンドが期待する可能性のあるスネークケースのフィールドも追加
      provider_id: data.providerId
    };
    
    try {
      const response = await apiClient.put<any>(`/api/v1/models/${modelId}`, processedData);
      console.log('API update model response:', response);
      
      // さまざまな形式のレスポンスを処理
      if (response) {
        // レスポンスがモデルオブジェクト自体である場合
        if (response.id && response.name && response.providerId) {
          return response as Model;
        }
        
        // レスポンスが{model: Model}の形式である場合
        if (typeof response === 'object' && 'model' in response && response.model) {
          return response.model as Model;
        }
        
        // レスポンスが他のオブジェクト内にモデル情報を含む場合
        const modelProps = ['id', 'name', 'providerId', 'displayName'];
        for (const key of Object.keys(response)) {
          const value = response[key];
          if (typeof value === 'object' && value !== null && 
              modelProps.every(prop => prop in value || prop.toLowerCase() in value)) {
            return value as Model;
          }
        }
      }
      
      // レスポンスの形式が期待と異なる場合でも処理を試みる
      return {
        id: modelId,
        providerId: data.providerId,
        name: data.name,
        displayName: data.displayName || data.name,
        description: data.description,
        isActive: data.isActive
      } as Model;
    } catch (error) {
      console.error('API error updating model:', error);
      throw error;
    }
  },

  // モデルの削除
  deleteModel: async (modelId: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/models/${modelId}`);
  }
};
