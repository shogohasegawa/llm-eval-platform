/**
 * Ollama関連の型定義
 */

export enum OllamaDownloadStatus {
  PENDING = 'pending',
  DOWNLOADING = 'downloading',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

/**
 * Ollamaモデルダウンロード情報
 */
export interface OllamaModelDownload {
  id: string;
  modelId: string;
  modelName: string;
  endpoint: string;
  status: OllamaDownloadStatus;
  progress: number;
  totalSize?: number;        // ダウンロード時の転送サイズ (バイト単位)
  downloadedSize?: number;   // ダウンロード済みの転送サイズ (バイト単位)
  modelSize?: number;        // モデルの実際のサイズ (バイト単位)
  modelSizeGb?: number;      // モデルの実際のサイズ (GB単位)
  error?: string | null;
  createdAt: string;
  updatedAt: string;
  completedAt?: string | null;
  digest?: string | null;
  modelInfo?: any;           // モデルの詳細情報
}

/**
 * Ollamaモデルダウンロードリクエスト
 */
export interface OllamaModelDownloadRequest {
  modelId: string;
  modelName: string;
  endpoint?: string;
}