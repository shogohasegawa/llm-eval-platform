import { v4 as uuidv4 } from 'uuid';
import DatabaseManager from './database';
import { Dataset, DatasetFormData, DatasetItem, DatasetItemFormData, DatasetType } from '../types/dataset';

/**
 * データセットリポジトリクラス
 * SQLiteデータベースとのやり取りを担当
 */
export class DatasetsRepository {
  private db = DatabaseManager.getInstance().getDb();

  /**
   * 全データセットを取得
   */
  getDatasets(): Dataset[] {
    const rows = this.db.prepare(`
      SELECT id, name, description, type, created_at, updated_at
      FROM datasets
      ORDER BY created_at DESC
    `).all();

    return rows.map(row => {
      const dataset = this.mapRowToDataset(row);
      // データセットアイテムの数を取得
      const itemCount = this.db.prepare(`
        SELECT COUNT(*) as count FROM dataset_items WHERE dataset_id = ?
      `).get(dataset.id);
      
      return {
        ...dataset,
        items: [], // 一覧取得時はアイテムは空配列
        itemCount: itemCount.count
      };
    });
  }

  /**
   * 特定のデータセットを取得
   */
  getDataset(id: string): Dataset | null {
    const row = this.db.prepare(`
      SELECT id, name, description, type, created_at, updated_at
      FROM datasets
      WHERE id = ?
    `).get(id);

    if (!row) return null;

    // データセットのアイテムも取得
    const items = this.getDatasetItems(id);
    
    return {
      ...this.mapRowToDataset(row),
      items
    };
  }

  /**
   * データセットを作成
   */
  createDataset(data: DatasetFormData): Dataset {
    const id = uuidv4();
    const now = new Date().toISOString();

    this.db.prepare(`
      INSERT INTO datasets (id, name, description, type, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(
      id,
      data.name,
      data.description || null,
      data.type,
      now,
      now
    );

    return {
      id,
      name: data.name,
      description: data.description,
      type: data.type as DatasetType,
      items: [],
      createdAt: new Date(now),
      updatedAt: new Date(now)
    };
  }

  /**
   * データセットを更新
   */
  updateDataset(id: string, data: DatasetFormData): Dataset | null {
    const dataset = this.getDataset(id);
    if (!dataset) return null;

    const now = new Date().toISOString();

    this.db.prepare(`
      UPDATE datasets
      SET name = ?, description = ?, type = ?, updated_at = ?
      WHERE id = ?
    `).run(
      data.name,
      data.description || null,
      data.type,
      now,
      id
    );

    return {
      ...dataset,
      name: data.name,
      description: data.description,
      type: data.type as DatasetType,
      updatedAt: new Date(now)
    };
  }

  /**
   * データセットを削除
   */
  deleteDataset(id: string): boolean {
    const result = this.db.prepare(`
      DELETE FROM datasets WHERE id = ?
    `).run(id);

    return result.changes > 0;
  }

  /**
   * データセットアイテムを取得
   */
  getDatasetItems(datasetId: string): DatasetItem[] {
    const rows = this.db.prepare(`
      SELECT id, dataset_id, input, expected_output, metadata, created_at, updated_at
      FROM dataset_items
      WHERE dataset_id = ?
      ORDER BY created_at ASC
    `).all(datasetId);

    return rows.map(row => this.mapRowToDatasetItem(row));
  }

  /**
   * データセットアイテムを取得
   */
  getDatasetItem(itemId: string): DatasetItem | null {
    const row = this.db.prepare(`
      SELECT id, dataset_id, input, expected_output, metadata, created_at, updated_at
      FROM dataset_items
      WHERE id = ?
    `).get(itemId);

    if (!row) return null;
    return this.mapRowToDatasetItem(row);
  }

  /**
   * データセットアイテムを追加
   */
  addDatasetItem(datasetId: string, data: DatasetItemFormData): DatasetItem {
    const id = uuidv4();
    const now = new Date().toISOString();
    const metadata = data.metadata ? JSON.stringify(data.metadata) : null;

    this.db.prepare(`
      INSERT INTO dataset_items (id, dataset_id, input, expected_output, metadata, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      datasetId,
      data.input,
      data.expectedOutput || null,
      metadata,
      now,
      now
    );

    // データセットの更新日時も更新
    this.db.prepare(`
      UPDATE datasets
      SET updated_at = ?
      WHERE id = ?
    `).run(now, datasetId);

    return {
      id,
      input: data.input,
      expectedOutput: data.expectedOutput,
      metadata: data.metadata
    };
  }

  /**
   * データセットアイテムを更新
   */
  updateDatasetItem(datasetId: string, itemId: string, data: DatasetItemFormData): DatasetItem | null {
    const item = this.getDatasetItem(itemId);
    if (!item) return null;

    const now = new Date().toISOString();
    const metadata = data.metadata ? JSON.stringify(data.metadata) : null;

    this.db.prepare(`
      UPDATE dataset_items
      SET input = ?, expected_output = ?, metadata = ?, updated_at = ?
      WHERE id = ? AND dataset_id = ?
    `).run(
      data.input,
      data.expectedOutput || null,
      metadata,
      now,
      itemId,
      datasetId
    );

    // データセットの更新日時も更新
    this.db.prepare(`
      UPDATE datasets
      SET updated_at = ?
      WHERE id = ?
    `).run(now, datasetId);

    return {
      ...item,
      input: data.input,
      expectedOutput: data.expectedOutput,
      metadata: data.metadata
    };
  }

  /**
   * データセットアイテムを削除
   */
  deleteDatasetItem(datasetId: string, itemId: string): boolean {
    const now = new Date().toISOString();
    
    const result = this.db.prepare(`
      DELETE FROM dataset_items WHERE id = ? AND dataset_id = ?
    `).run(itemId, datasetId);

    if (result.changes > 0) {
      // データセットの更新日時を更新
      this.db.prepare(`
        UPDATE datasets
        SET updated_at = ?
        WHERE id = ?
      `).run(now, datasetId);
      
      return true;
    }
    
    return false;
  }

  /**
   * データベースのレコードをDatasetオブジェクトに変換
   */
  private mapRowToDataset(row: any): Dataset {
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      type: row.type as DatasetType,
      items: [], // 初期化時は空配列
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at)
    };
  }

  /**
   * データベースのレコードをDatasetItemオブジェクトに変換
   */
  private mapRowToDatasetItem(row: any): DatasetItem {
    return {
      id: row.id,
      input: row.input,
      expectedOutput: row.expected_output,
      metadata: row.metadata ? JSON.parse(row.metadata) : undefined
    };
  }

  /**
   * JSONからデータセットをインポート
   */
  importFromJson(jsonData: string): Dataset | null {
    try {
      const data = JSON.parse(jsonData);
      if (!data.name || !data.type || !Array.isArray(data.items)) {
        throw new Error('Invalid dataset format');
      }

      // トランザクションを開始
      const transaction = this.db.transaction(() => {
        // データセットを作成
        const dataset = this.createDataset({
          name: data.name,
          description: data.description,
          type: data.type as DatasetType
        });

        // アイテムを追加
        data.items.forEach((item: any) => {
          this.addDatasetItem(dataset.id, {
            input: item.input,
            expectedOutput: item.expectedOutput,
            metadata: item.metadata
          });
        });

        return dataset;
      });

      return transaction();
    } catch (error) {
      console.error('Failed to import dataset:', error);
      return null;
    }
  }

  /**
   * データセットをJSONにエクスポート
   */
  exportToJson(id: string): string | null {
    const dataset = this.getDataset(id);
    if (!dataset) return null;

    return JSON.stringify({
      name: dataset.name,
      description: dataset.description,
      type: dataset.type,
      items: dataset.items
    });
  }
}

export const datasetsRepository = new DatasetsRepository();
