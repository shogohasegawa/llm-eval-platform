import { v4 as uuidv4 } from 'uuid';
import DatabaseManager from './database';
import { Provider, ProviderFormData, Model, ModelFormData, ProviderType } from '../types/provider';

/**
 * プロバイダリポジトリクラス
 * SQLiteデータベースとのやり取りを担当
 */
export class ProvidersRepository {
  private db = DatabaseManager.getInstance().getDb();

  /**
   * 全プロバイダを取得
   */
  getProviders(): Provider[] {
    const rows = this.db.prepare(`
      SELECT id, name, type, endpoint, api_key, is_active, created_at, updated_at
      FROM providers
      ORDER BY created_at DESC
    `).all();

    return rows.map(row => this.mapRowToProvider(row));
  }

  /**
   * 特定のプロバイダを取得
   */
  getProvider(id: string): Provider | null {
    const row = this.db.prepare(`
      SELECT id, name, type, endpoint, api_key, is_active, created_at, updated_at
      FROM providers
      WHERE id = ?
    `).get(id);

    if (!row) return null;
    
    return this.mapRowToProvider(row);
  }

  /**
   * プロバイダを作成
   */
  createProvider(data: ProviderFormData): Provider {
    const id = uuidv4();
    const now = new Date().toISOString();

    this.db.prepare(`
      INSERT INTO providers (id, name, type, endpoint, api_key, is_active, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      data.name,
      data.type,
      data.endpoint || null,
      data.apiKey || null,
      data.isActive ? 1 : 0,
      now,
      now
    );

    return {
      id,
      name: data.name,
      type: data.type as ProviderType,
      endpoint: data.endpoint,
      apiKey: data.apiKey,
      isActive: data.isActive,
      createdAt: new Date(now),
      updatedAt: new Date(now)
    };
  }

  /**
   * プロバイダを更新
   */
  updateProvider(id: string, data: ProviderFormData): Provider | null {
    const provider = this.getProvider(id);
    if (!provider) return null;

    const now = new Date().toISOString();

    this.db.prepare(`
      UPDATE providers
      SET name = ?, type = ?, endpoint = ?, api_key = ?, is_active = ?, updated_at = ?
      WHERE id = ?
    `).run(
      data.name,
      data.type,
      data.endpoint || null,
      data.apiKey || null,
      data.isActive ? 1 : 0,
      now,
      id
    );

    return {
      ...provider,
      name: data.name,
      type: data.type as ProviderType,
      endpoint: data.endpoint,
      apiKey: data.apiKey,
      isActive: data.isActive,
      updatedAt: new Date(now)
    };
  }

  /**
   * プロバイダを削除
   */
  deleteProvider(id: string): boolean {
    const result = this.db.prepare(`
      DELETE FROM providers WHERE id = ?
    `).run(id);

    return result.changes > 0;
  }

  /**
   * プロバイダのモデル一覧を取得
   */
  getProviderModels(providerId: string): Model[] {
    const rows = this.db.prepare(`
      SELECT id, provider_id, name, display_name, description, endpoint, api_key, parameters, is_active, created_at, updated_at
      FROM models
      WHERE provider_id = ?
      ORDER BY created_at DESC
    `).all(providerId);

    return rows.map(row => this.mapRowToModel(row));
  }

  /**
   * モデルを取得
   */
  getModel(modelId: string): Model | null {
    const row = this.db.prepare(`
      SELECT id, provider_id, name, display_name, description, endpoint, api_key, parameters, is_active, created_at, updated_at
      FROM models
      WHERE id = ?
    `).get(modelId);

    if (!row) return null;
    return this.mapRowToModel(row);
  }

  /**
   * モデルを作成
   */
  createModel(data: ModelFormData): Model {
    const id = uuidv4();
    const now = new Date().toISOString();
    const parameters = data.parameters ? JSON.stringify(data.parameters) : null;

    this.db.prepare(`
      INSERT INTO models (id, provider_id, name, display_name, description, endpoint, api_key, parameters, is_active, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      data.providerId,
      data.name,
      data.displayName,
      data.description || null,
      data.endpoint || null,
      data.apiKey || null,
      parameters,
      data.isActive ? 1 : 0,
      now,
      now
    );

    return {
      id,
      providerId: data.providerId,
      name: data.name,
      displayName: data.displayName,
      description: data.description,
      endpoint: data.endpoint,
      apiKey: data.apiKey,
      parameters: data.parameters,
      isActive: data.isActive,
      createdAt: new Date(now),
      updatedAt: new Date(now)
    };
  }

  /**
   * モデルを更新
   */
  updateModel(modelId: string, data: ModelFormData): Model | null {
    const model = this.getModel(modelId);
    if (!model) return null;

    const now = new Date().toISOString();
    const parameters = data.parameters ? JSON.stringify(data.parameters) : null;

    this.db.prepare(`
      UPDATE models
      SET provider_id = ?, name = ?, display_name = ?, description = ?, endpoint = ?, api_key = ?, parameters = ?, is_active = ?, updated_at = ?
      WHERE id = ?
    `).run(
      data.providerId,
      data.name,
      data.displayName,
      data.description || null,
      data.endpoint || null,
      data.apiKey || null,
      parameters,
      data.isActive ? 1 : 0,
      now,
      modelId
    );

    return {
      ...model,
      providerId: data.providerId,
      name: data.name,
      displayName: data.displayName,
      description: data.description,
      endpoint: data.endpoint,
      apiKey: data.apiKey,
      parameters: data.parameters,
      isActive: data.isActive,
      updatedAt: new Date(now)
    };
  }

  /**
   * モデルを削除
   */
  deleteModel(modelId: string): boolean {
    const result = this.db.prepare(`
      DELETE FROM models WHERE id = ?
    `).run(modelId);

    return result.changes > 0;
  }

  /**
   * プロバイダの検証（モック実装）
   */
  validateProvider(type: string, endpoint?: string, apiKey?: string): boolean {
    console.log(`Validating provider of type '${type}' with endpoint '${endpoint}' and apiKey '${apiKey ? '***' : ''}'`);
    // 常に成功を返すモック実装
    return true;
  }

  /**
   * データベースのレコードをProviderオブジェクトに変換
   */
  private mapRowToProvider(row: any): Provider {
    return {
      id: row.id,
      name: row.name,
      type: row.type as ProviderType,
      endpoint: row.endpoint,
      apiKey: row.api_key,
      isActive: Boolean(row.is_active),
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at)
    };
  }

  /**
   * データベースのレコードをModelオブジェクトに変換
   */
  private mapRowToModel(row: any): Model {
    return {
      id: row.id,
      providerId: row.provider_id,
      name: row.name,
      displayName: row.display_name,
      description: row.description,
      endpoint: row.endpoint,
      apiKey: row.api_key,
      parameters: row.parameters ? JSON.parse(row.parameters) : undefined,
      isActive: Boolean(row.is_active),
      createdAt: row.created_at ? new Date(row.created_at) : undefined,
      updatedAt: row.updated_at ? new Date(row.updated_at) : undefined
    };
  }
}

export const providersRepository = new ProvidersRepository();
