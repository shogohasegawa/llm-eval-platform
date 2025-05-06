/**
 * Ollama API クライアント
 * バックエンドの /api/v1/ollama エンドポイントと連携
 */
import { apiClient } from './client';
import { OllamaModelDownload } from '../types/ollama';

export const ollamaApi = {
  /**
   * Ollamaモデルのダウンロードを開始
   * @param modelId - モデルID
   * @param modelName - モデル名
   * @param endpoint - エンドポイント（オプション）
   * @returns ダウンロード情報
   */
  downloadModel: async (
    modelId: string,
    modelName: string,
    endpoint?: string
  ): Promise<OllamaModelDownload> => {
    try {
      const response = await apiClient.post<any>('/api/v1/ollama/download', {
        model_id: modelId,
        model_name: modelName,
        endpoint: endpoint
      });
      
      console.log('Ollama download model response:', response);
      
      // レスポンスがオブジェクト形式の場合
      if (response && typeof response === 'object') {
        return {
          id: response.download_id || response.id,
          modelId: response.model_id || modelId,
          modelName: response.model_name || modelName,
          status: response.status,
          progress: response.progress || 0,
          endpoint: response.endpoint || endpoint || '',
          createdAt: response.created_at || new Date().toISOString(),
          updatedAt: response.updated_at || new Date().toISOString()
        };
      }
      
      throw new Error('Ollama model download failed: Unexpected response format');
    } catch (error) {
      console.error('Error downloading Ollama model:', error);
      throw error;
    }
  },
  
  /**
   * ダウンロード情報を取得
   * @param downloadId - ダウンロードID
   * @returns ダウンロード情報
   */
  getDownloadStatus: async (downloadId: string): Promise<OllamaModelDownload> => {
    try {
      const response = await apiClient.get<any>(`/api/v1/ollama/download/${downloadId}`);
      
      console.log('Ollama download status response:', response);
      
      // レスポンスがオブジェクト形式の場合
      if (response && typeof response === 'object') {
        return {
          id: response.id,
          modelId: response.model_id,
          modelName: response.model_name,
          status: response.status,
          progress: response.progress || 0,
          totalSize: response.total_size || 0,
          downloadedSize: response.downloaded_size || 0,
          modelSize: response.model_size || 0,
          modelSizeGb: response.model_size_gb || 0.0,
          error: response.error,
          endpoint: response.endpoint || '',
          createdAt: response.created_at,
          updatedAt: response.updated_at,
          completedAt: response.completed_at,
          digest: response.digest,
          modelInfo: response.model_info
        };
      }
      
      throw new Error('Could not retrieve download status: Unexpected response format');
    } catch (error) {
      console.error('Error getting Ollama download status:', error);
      throw error;
    }
  },
  
  /**
   * モデルIDに関連するすべてのダウンロード情報を取得
   * @param modelId - モデルID
   * @returns ダウンロード情報の配列
   */
  getModelDownloads: async (modelId: string): Promise<OllamaModelDownload[]> => {
    try {
      const response = await apiClient.get<any>(`/api/v1/ollama/downloads/model/${modelId}`);
      
      console.log('Ollama model downloads response:', response);
      
      // 共通のマッピング関数
      const mapItem = (item: any): OllamaModelDownload => ({
        id: item.id,
        modelId: item.model_id,
        modelName: item.model_name,
        status: item.status,
        progress: item.progress || 0,
        totalSize: item.total_size || 0,
        downloadedSize: item.downloaded_size || 0,
        modelSize: item.model_size || 0,
        modelSizeGb: item.model_size_gb || 0.0,
        error: item.error,
        endpoint: item.endpoint || '',
        createdAt: item.created_at,
        updatedAt: item.updated_at,
        completedAt: item.completed_at,
        digest: item.digest,
        modelInfo: item.model_info
      });
      
      // レスポンスが配列形式の場合
      if (Array.isArray(response)) {
        return response.map(mapItem);
      }
      
      // レスポンスがオブジェクトでdownloadsプロパティがある場合
      if (response && typeof response === 'object' && 'downloads' in response && Array.isArray(response.downloads)) {
        return response.downloads.map(mapItem);
      }
      
      return [];
    } catch (error) {
      console.error('Error getting Ollama model downloads:', error);
      return [];
    }
  },
  
  /**
   * モデルが存在するかチェック
   * @param modelName - モデル名
   * @param endpoint - エンドポイント
   * @returns チェック結果
   */
  checkModelExists: async (modelName: string, endpoint?: string): Promise<{exists: boolean, modelInfo?: any, availableModels?: string[]}> => {
    try {
      const params = new URLSearchParams({
        model_name: modelName
      });
      
      if (endpoint) {
        params.append('endpoint', endpoint);
      }
      
      const response = await apiClient.get<any>(`/api/v1/ollama/check_model?${params.toString()}`);
      
      console.log('Ollama check model response:', response);
      
      return {
        exists: response.exists || false,
        modelInfo: response.model_info,
        availableModels: response.available_models
      };
    } catch (error) {
      console.error('Error checking Ollama model existence:', error);
      return { exists: false };
    }
  },
  
  /**
   * すべてのダウンロード情報を取得
   * @returns ダウンロード情報の配列
   */
  getAllDownloads: async (): Promise<OllamaModelDownload[]> => {
    try {
      const response = await apiClient.get<any>('/api/v1/ollama/downloads');
      
      console.log('Ollama all downloads response:', response);
      
      // 共通のマッピング関数
      const mapItem = (item: any): OllamaModelDownload => ({
        id: item.id,
        modelId: item.model_id,
        modelName: item.model_name,
        status: item.status,
        progress: item.progress || 0,
        totalSize: item.total_size || 0,
        downloadedSize: item.downloaded_size || 0,
        modelSize: item.model_size || 0,
        modelSizeGb: item.model_size_gb || 0.0,
        error: item.error,
        endpoint: item.endpoint || '',
        createdAt: item.created_at,
        updatedAt: item.updated_at,
        completedAt: item.completed_at,
        digest: item.digest,
        modelInfo: item.model_info
      });
      
      // レスポンスが配列形式の場合
      if (Array.isArray(response)) {
        return response.map(mapItem);
      }
      
      // レスポンスがオブジェクトでdownloadsプロパティがある場合
      if (response && typeof response === 'object' && 'downloads' in response && Array.isArray(response.downloads)) {
        return response.downloads.map(mapItem);
      }
      
      return [];
    } catch (error) {
      console.error('Error getting all Ollama downloads:', error);
      return [];
    }
  }
};