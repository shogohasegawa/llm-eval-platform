/**
 * LLMプロバイダとモデルの型定義
 */

export interface Provider {
  id: string;
  provider_id?: string; // バックエンドがスネークケースで返す場合
  name: string;
  type: string; // プロバイダタイプ（例：openai, anthropic, ollama, custom）
  endpoint?: string;
  apiKey?: string;
  api_key?: string; // バックエンドがスネークケースで返す場合
  isActive: boolean;
  is_active?: boolean; // バックエンドがスネークケースで返す場合
  createdAt?: string;
  created_at?: string; // バックエンドがスネークケースで返す場合
  updatedAt?: string;
  updated_at?: string; // バックエンドがスネークケースで返す場合
  models?: Model[]; // プロバイダに関連付けられたモデルのリスト
  modelCount?: number; // モデル数（UIで使用）
}

export interface Model {
  id: string;
  model_id?: string; // バックエンドがスネークケースで返す場合
  providerId: string;
  provider_id?: string; // バックエンドがスネークケースで返す場合
  name: string;
  displayName: string;
  display_name?: string; // バックエンドがスネークケースで返す場合
  description?: string;
  endpoint?: string;
  apiKey?: string;
  api_key?: string; // バックエンドがスネークケースで返す場合
  parameters?: Record<string, any>;
  isActive: boolean;
  is_active?: boolean; // バックエンドがスネークケースで返す場合
  createdAt?: string;
  created_at?: string; // バックエンドがスネークケースで返す場合
  updatedAt?: string;
  updated_at?: string; // バックエンドがスネークケースで返す場合
  providerName?: string; // APIレスポンスから追加される場合がある
}

export interface ProviderFormData {
  name: string;
  type?: string; // プロバイダタイプ（自動設定されるが、明示的に指定することも可能）
  endpoint?: string;
  apiKey?: string;
  isActive: boolean;
}

export interface ModelFormData {
  providerId: string;
  name: string;
  displayName: string;
  description?: string;
  endpoint?: string;
  apiKey?: string;
  parameters?: Record<string, any>;
  isActive: boolean;
}
