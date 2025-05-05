/**
 * LLMプロバイダとモデルの型定義
 */

export interface Provider {
  id: string;
  name: string;
  type: string; // プロバイダタイプ（例：openai, anthropic, ollama, custom）
  endpoint?: string;
  apiKey?: string;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
  models?: Model[]; // プロバイダに関連付けられたモデルのリスト
}

export interface Model {
  id: string;
  providerId: string;
  name: string;
  displayName: string;
  description?: string;
  endpoint?: string;
  apiKey?: string;
  parameters?: Record<string, any>;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
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
