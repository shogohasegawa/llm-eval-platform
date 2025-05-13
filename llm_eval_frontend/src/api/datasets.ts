import { apiClient } from './client';
import { Dataset, DatasetFormData, DatasetItem, DatasetUploadType } from '../types/dataset';

/**
 * データセットAPI
 */
export const datasetsApi = {
  // データセット一覧の取得
  getDatasets: async (type?: string): Promise<Dataset[]> => {
    const params = type ? { type } : undefined;
    const response = await apiClient.get('/api/v1/datasets', { params });
    return response.datasets || [];
  },

  // 特定のデータセットの取得（名前とタイプベース）
  getDatasetByName: async (name: string, type?: string): Promise<Dataset> => {
    const params = type ? { type } : undefined;
    const response = await apiClient.get(`/api/v1/datasets/${name}`, { params });

    // メタデータに加えてデータセットレベルの属性（instruction, metrics, output_length）を引き継ぐ
    return {
      ...response.metadata,
      // 明示的にメタデータから各属性を抽出
      instruction: response.metadata?.instruction,
      metrics: response.metadata?.metrics,
      output_length: response.metadata?.output_length,
      // 配列の場合の安全な処理
      items: response.items || [],
      // 表示設定も引き継ぐ
      display_config: response.display_config,
    };
  },

  // データセットの削除
  deleteDataset: async (filePath: string): Promise<void> => {
    await apiClient.delete(`/api/v1/datasets/by-path?file_path=${filePath}`);
  },

  // JSONファイルをアップロード
  uploadJsonFile: async (file: File, type: DatasetUploadType): Promise<Dataset> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('dataset_type', type);

    const response = await apiClient.post('/api/v1/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    // メタデータに加えてデータセットレベルの属性（instruction, metrics, output_length）を引き継ぐ
    return {
      ...response.metadata,
      // 明示的にメタデータから各属性を抽出
      instruction: response.metadata?.instruction,
      metrics: response.metadata?.metrics,
      output_length: response.metadata?.output_length,
      // 配列の場合の安全な処理
      items: response.items || [],
      // 表示設定も引き継ぐ
      display_config: response.display_config,
    };
  }
};
