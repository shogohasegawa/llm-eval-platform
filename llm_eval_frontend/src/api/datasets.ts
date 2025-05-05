import { apiClient } from './client';
import { Dataset, DatasetFormData, DatasetItem, DatasetUploadType } from '../types/dataset';

/**
 * データセットAPI
 */
export const datasetsApi = {
  // データセット一覧の取得
  getDatasets: async (type?: string): Promise<Dataset[]> => {
    const params = type ? { type } : undefined;
    const response = await apiClient.get('/api/datasets', { params });
    return response.datasets || [];
  },

  // 特定のデータセットの取得（名前ベース）
  getDatasetByName: async (name: string): Promise<Dataset> => {
    const response = await apiClient.get(`/api/datasets/${name}`);
    return {
      ...response.metadata,
      items: response.items || [],
    };
  },

  // データセットの削除
  deleteDataset: async (filePath: string): Promise<void> => {
    await apiClient.delete(`/api/datasets/by-path?file_path=${filePath}`);
  },

  // JSONファイルをアップロード
  uploadJsonFile: async (file: File, type: DatasetUploadType): Promise<Dataset> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('dataset_type', type);
    
    const response = await apiClient.post('/api/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return {
      ...response.metadata,
      items: response.items || [],
    };
  }
};
