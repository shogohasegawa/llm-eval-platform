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
}

export interface DatasetListResponse {
  datasets: DatasetMetadata[];
}

export interface DatasetDetailResponse {
  metadata: DatasetMetadata;
  items: DatasetItem[];
}

export interface DatasetDeleteResponse {
  success: boolean;
  message: string;
}
