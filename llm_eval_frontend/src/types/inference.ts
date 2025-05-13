/**
 * 推論実行の型定義
 */

export type InferenceStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ModelConfig {
  provider: string;      // プロバイダタイプ (openai, anthropic, ollama など)
  model_name: string;    // モデル名
  max_tokens: number;    // 最大トークン数
  temperature?: number;  // 温度パラメータ
  top_p?: number;        // Top-p サンプリングパラメータ
  additional_params?: Record<string, any>; // その他の追加パラメータ
}

export interface EvaluationRequest {
  datasets: string[];    // 評価対象のデータセット名一覧
  num_samples: number;   // 評価サンプル数
  n_shots: number[];     // few-shot数リスト
  model: ModelConfig;    // モデル設定
}

export interface EvaluationResponse {
  model_info: ModelConfig;    // 使用したモデル情報
  metrics: Record<string, number>; // フラットメトリクス辞書
}

export interface Inference {
  id: string;
  name: string;
  description?: string;
  datasetId: string;
  providerId: string;
  modelId: string;
  // 表示用の追加フィールド
  providerName?: string;
  providerType?: string;
  modelName?: string;
  status: InferenceStatus;
  progress: number; // 0-100
  results: InferenceResult[];
  metrics?: Record<string, number>;
  createdAt: string | Date;
  updatedAt: string | Date;
  completedAt?: string | Date;
  error?: string;
}

export interface InferenceResult {
  id: string;
  datasetItemId: string;
  input: string;
  expectedOutput?: string;
  actualOutput: string;
  metrics?: Record<string, number>;
  metadata?: Record<string, any>;
  error?: string;
  latency?: number; // ミリ秒
  tokenCount?: number;
}

export interface InferenceFormData {
  name: string;
  description?: string;
  datasetId: string;
  datasetType?: string;  // データセットタイプ（'test' または 'n_shot'）
  providerId: string;
  modelId: string;
  // 評価パラメータ（オプション）
  numSamples?: number;   // サンプル数（デフォルト: 100）
  nShots?: number;       // Few-shotの数（デフォルト: 0）
  maxTokens?: number;    // 最大トークン数（デフォルト: 512）
  temperature?: number;  // 温度パラメータ（デフォルト: 0.7）
  topP?: number;         // Top-pサンプリング（デフォルト: 1.0）
  // JSONL形式データセット用
  isJsonlDataset?: boolean; // JSONLデータセットフラグ
  // バックエンドAPI用のスネークケース形式フィールド
  dataset_type?: string; // データセットタイプ（'test' または 'n_shot'）
}

export interface InferenceFilterOptions {
  datasetId?: string;
  providerId?: string;
  modelId?: string;
  status?: InferenceStatus;
}

export interface AdvancedEvaluationFormData extends InferenceFormData {
  numSamples: number;  // サンプル数（必須）
  nShots: number[];    // Few-shotの数リスト（必須）
  maxTokens: number;   // 最大トークン数（必須）
  temperature: number; // 温度パラメータ（必須）
  topP: number;        // Top-pサンプリング（必須）
}
