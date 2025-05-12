/**
 * データセットの型定義
 */

export type DatasetUploadType = 'test' | 'n_shot';

export interface Dataset {
  id?: string;
  name: string;
  description?: string;
  type: string;
  created_at?: Date;
  createdAt?: Date;
  updatedAt?: Date;
  itemCount?: number;
  item_count?: number;
  file_path?: string;
  items: DatasetItem[];
  // データセットレベルのプロパティ
  instruction?: string;
  metrics?: string[] | Record<string, any> | string;
  output_length?: number;
  samples?: DatasetItem[];
  // 表示用設定
  display_config?: DisplayConfig;
}

export interface DatasetItem {
  id: string;
  instruction: string;
  input?: string;
  output?: string;
  additional_data?: Record<string, any>;
}

export interface DatasetFormData {
  name: string;
  description?: string;
  type: string;
}

export interface DatasetMetadata {
  name: string;
  description: string;
  type: string;
  created_at: Date;
  item_count: number;
  file_path: string;
  additional_props?: Record<string, any>;
}

export interface DatasetListResponse {
  datasets: DatasetMetadata[];
}

export interface DisplayConfig {
  file_format: 'json' | 'jsonl';
  labels: {
    primary: string;
    secondary: string;
    tertiary: string;
  };
}

export interface DatasetDetailResponse {
  metadata: DatasetMetadata;
  items: DatasetItem[];
  display_config?: DisplayConfig;
}

export interface DatasetDeleteResponse {
  success: boolean;
  message: string;
}
