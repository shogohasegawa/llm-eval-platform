import { v4 as uuidv4 } from 'uuid';
import DatabaseManager from './database';
import { 
  Inference, 
  InferenceFormData, 
  InferenceResult, 
  InferenceStatus,
  InferenceFilterOptions 
} from '../types/inference';
import { providersRepository } from './providers.repository';
import { datasetsRepository } from './datasets.repository';

/**
 * 推論リポジトリクラス
 * SQLiteデータベースとのやり取りを担当
 */
export class InferencesRepository {
  private db = DatabaseManager.getInstance().getDb();

  /**
   * 全推論を取得
   */
  getInferences(filters?: InferenceFilterOptions): Inference[] {
    let query = `
      SELECT id, name, description, dataset_id, provider_id, model_id, status, progress, 
             metrics, created_at, updated_at, completed_at, error
      FROM inferences
      WHERE 1=1
    `;
    
    const params: any[] = [];
    
    // フィルタ条件を追加
    if (filters) {
      if (filters.datasetId) {
        query += ' AND dataset_id = ?';
        params.push(filters.datasetId);
      }
      
      if (filters.providerId) {
        query += ' AND provider_id = ?';
        params.push(filters.providerId);
      }
      
      if (filters.modelId) {
        query += ' AND model_id = ?';
        params.push(filters.modelId);
      }
      
      if (filters.status) {
        query += ' AND status = ?';
        params.push(filters.status);
      }
    }
    
    query += ' ORDER BY created_at DESC';
    
    const rows = this.db.prepare(query).all(...params);
    
    return rows.map(row => {
      // 関連データの件数を取得
      const resultCount = this.db.prepare(`
        SELECT COUNT(*) as count FROM inference_results WHERE inference_id = ?
      `).get(row.id);
      
      const inference = this.mapRowToInference(row);
      return {
        ...inference,
        results: [], // 一覧取得時は空配列
        resultCount: resultCount.count
      };
    });
  }

  /**
   * 特定の推論を取得
   */
  getInference(id: string): Inference | null {
    const row = this.db.prepare(`
      SELECT id, name, description, dataset_id, provider_id, model_id, status, progress, 
             metrics, created_at, updated_at, completed_at, error
      FROM inferences
      WHERE id = ?
    `).get(id);

    if (!row) return null;

    // 推論結果を取得（具体的なレコード数によって非効率になる可能性あり）
    const results = this.getInferenceResults(id);
    
    return {
      ...this.mapRowToInference(row),
      results
    };
  }

  /**
   * 推論を作成
   */
  createInference(data: InferenceFormData): Inference {
    const id = uuidv4();
    const now = new Date().toISOString();

    this.db.prepare(`
      INSERT INTO inferences (
        id, name, description, dataset_id, provider_id, model_id, 
        status, progress, created_at, updated_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      data.name,
      data.description || null,
      data.datasetId,
      data.providerId,
      data.modelId,
      'pending' as InferenceStatus,
      0,
      now,
      now
    );

    // 追加情報を取得
    const provider = providersRepository.getProvider(data.providerId);
    const model = providersRepository.getModel(data.modelId);

    return {
      id,
      name: data.name,
      description: data.description,
      datasetId: data.datasetId,
      providerId: data.providerId,
      modelId: data.modelId,
      status: 'pending',
      progress: 0,
      results: [],
      provider: provider ? {
        name: provider.name,
        type: provider.type
      } : undefined,
      model: model ? {
        name: model.name,
        displayName: model.displayName
      } : undefined,
      createdAt: new Date(now),
      updatedAt: new Date(now)
    };
  }

  /**
   * 推論を更新
   */
  updateInference(id: string, data: Partial<InferenceFormData>): Inference | null {
    const inference = this.getInference(id);
    if (!inference) return null;

    const now = new Date().toISOString();
    const fields: string[] = [];
    const values: any[] = [];

    // 更新するフィールドを設定
    if (data.name !== undefined) {
      fields.push('name = ?');
      values.push(data.name);
    }

    if (data.description !== undefined) {
      fields.push('description = ?');
      values.push(data.description || null);
    }

    if (data.datasetId !== undefined) {
      fields.push('dataset_id = ?');
      values.push(data.datasetId);
    }

    if (data.providerId !== undefined) {
      fields.push('provider_id = ?');
      values.push(data.providerId);
    }

    if (data.modelId !== undefined) {
      fields.push('model_id = ?');
      values.push(data.modelId);
    }

    fields.push('updated_at = ?');
    values.push(now);
    values.push(id);

    if (fields.length > 1) {
      this.db.prepare(`
        UPDATE inferences
        SET ${fields.join(', ')}
        WHERE id = ?
      `).run(...values);
    }

    return {
      ...inference,
      name: data.name !== undefined ? data.name : inference.name,
      description: data.description !== undefined ? data.description : inference.description,
      datasetId: data.datasetId !== undefined ? data.datasetId : inference.datasetId,
      providerId: data.providerId !== undefined ? data.providerId : inference.providerId,
      modelId: data.modelId !== undefined ? data.modelId : inference.modelId,
      updatedAt: new Date(now)
    };
  }

  /**
   * 推論を削除
   */
  deleteInference(id: string): boolean {
    const result = this.db.prepare(`
      DELETE FROM inferences WHERE id = ?
    `).run(id);

    return result.changes > 0;
  }

  /**
   * 推論のステータスを更新
   */
  updateInferenceStatus(id: string, status: InferenceStatus, progress: number, error?: string): Inference | null {
    const inference = this.getInference(id);
    if (!inference) return null;

    const now = new Date().toISOString();
    let completedAt = null;

    if (status === 'completed') {
      completedAt = now;
    }

    this.db.prepare(`
      UPDATE inferences
      SET status = ?, progress = ?, updated_at = ?, completed_at = ?, error = ?
      WHERE id = ?
    `).run(
      status,
      progress,
      now,
      completedAt,
      error || null,
      id
    );

    return {
      ...inference,
      status,
      progress,
      error,
      updatedAt: new Date(now),
      completedAt: completedAt ? new Date(completedAt) : undefined
    };
  }

  /**
   * 推論結果を取得
   */
  getInferenceResults(inferenceId: string): InferenceResult[] {
    const rows = this.db.prepare(`
      SELECT id, inference_id, dataset_item_id, input, expected_output, actual_output,
             metrics, metadata, error, latency, token_count, created_at
      FROM inference_results
      WHERE inference_id = ?
      ORDER BY created_at ASC
    `).all(inferenceId);

    return rows.map(row => this.mapRowToInferenceResult(row));
  }

  /**
   * 特定の推論結果を取得
   */
  getInferenceResult(inferenceId: string, resultId: string): InferenceResult | null {
    const row = this.db.prepare(`
      SELECT id, inference_id, dataset_item_id, input, expected_output, actual_output,
             metrics, metadata, error, latency, token_count, created_at
      FROM inference_results
      WHERE inference_id = ? AND id = ?
    `).get(inferenceId, resultId);

    if (!row) return null;
    return this.mapRowToInferenceResult(row);
  }

  /**
   * 推論結果を追加
   */
  addInferenceResult(inferenceId: string, result: Partial<InferenceResult>): InferenceResult {
    const id = uuidv4();
    const now = new Date().toISOString();
    const metrics = result.metrics ? JSON.stringify(result.metrics) : null;
    const metadata = result.metadata ? JSON.stringify(result.metadata) : null;

    this.db.prepare(`
      INSERT INTO inference_results (
        id, inference_id, dataset_item_id, input, expected_output, actual_output,
        metrics, metadata, error, latency, token_count, created_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      inferenceId,
      result.datasetItemId,
      result.input,
      result.expectedOutput || null,
      result.actualOutput,
      metrics,
      metadata,
      result.error || null,
      result.latency || null,
      result.tokenCount || null,
      now
    );

    // 推論の更新日時とプログレスを更新
    const inference = this.getInference(inferenceId);
    if (inference) {
      const totalItems = this.getTotalDatasetItems(inference.datasetId);
      const completedItems = this.getCompletedResultsCount(inferenceId);
      const progress = totalItems > 0 ? Math.floor((completedItems / totalItems) * 100) : 0;

      this.db.prepare(`
        UPDATE inferences
        SET updated_at = ?, progress = ?
        WHERE id = ?
      `).run(now, progress, inferenceId);
    }

    return {
      id,
      datasetItemId: result.datasetItemId!,
      input: result.input!,
      expectedOutput: result.expectedOutput,
      actualOutput: result.actualOutput!,
      metrics: result.metrics,
      metadata: result.metadata,
      error: result.error,
      latency: result.latency,
      tokenCount: result.tokenCount
    };
  }

  /**
   * 推論結果を削除（主に再実行時にクリアするため）
   */
  deleteInferenceResults(inferenceId: string): boolean {
    const result = this.db.prepare(`
      DELETE FROM inference_results WHERE inference_id = ?
    `).run(inferenceId);

    return result.changes > 0;
  }

  /**
   * 推論の実行（この関数は実際のLLM API呼び出しはシミュレートします）
   */
  async runInference(id: string): Promise<boolean> {
    const inference = this.getInference(id);
    if (!inference || inference.status === 'running') return false;

    // ステータスを実行中に更新
    this.updateInferenceStatus(id, 'running', 0);

    // データセットアイテムを取得
    const dataset = datasetsRepository.getDataset(inference.datasetId);
    if (!dataset || !dataset.items.length) {
      this.updateInferenceStatus(id, 'failed', 0, 'Dataset is empty');
      return false;
    }

    // 既存の結果をクリア
    this.deleteInferenceResults(id);

    // 非同期処理でアイテムを順次処理
    setTimeout(() => {
      this.processInferenceItems(inference, dataset.items);
    }, 0);

    return true;
  }

  /**
   * 推論アイテムの処理（シミュレーション）
   */
  private async processInferenceItems(inference: Inference, items: any[]): Promise<void> {
    let processed = 0;

    for (const item of items) {
      // 処理がキャンセルされていないか確認
      const currentInference = this.getInference(inference.id);
      if (!currentInference || currentInference.status !== 'running') {
        break;
      }

      // モックのレスポンス生成
      const response = this.mockLLMResponse(item.input, inference.modelId);
      const latency = Math.random() * 1000 + 500; // 500〜1500msのランダムなレイテンシ

      // 結果を保存
      this.addInferenceResult(inference.id, {
        datasetItemId: item.id,
        input: item.input,
        expectedOutput: item.expectedOutput,
        actualOutput: response,
        latency,
        tokenCount: Math.floor(response.length / 4)
      });

      processed++;
      const progress = Math.floor((processed / items.length) * 100);
      this.updateInferenceStatus(inference.id, 'running', progress);

      // 処理間の遅延をシミュレート（実際のAPIでは並列処理も可能）
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    // 完了した推論のステータスを更新
    this.updateInferenceStatus(inference.id, 'completed', 100);
  }

  /**
   * モックLLMレスポンスの生成（実際のAPIを使用する場合はここを置き換え）
   */
  private mockLLMResponse(input: string, modelId: string): string {
    // 入力から簡単なレスポンスを生成
    const responses = [
      `Based on the input "${input.substring(0, 20)}...", here's my analysis`,
      `The answer to your question is: it depends on various factors`,
      `I've considered your input and believe that the most appropriate response is`,
      `Let me think about "${input.substring(0, 15)}..." for a moment`,
      `This is an interesting question. My response is that`,
    ];
    
    const randomIndex = Math.floor(Math.random() * responses.length);
    return `${responses[randomIndex]}... [additional response text would be generated by the real model]`;
  }

  /**
   * データセットのアイテム数を取得
   */
  private getTotalDatasetItems(datasetId: string): number {
    const result = this.db.prepare(`
      SELECT COUNT(*) as count FROM dataset_items WHERE dataset_id = ?
    `).get(datasetId);
    
    return result ? result.count : 0;
  }

  /**
   * 完了した結果の数を取得
   */
  private getCompletedResultsCount(inferenceId: string): number {
    const result = this.db.prepare(`
      SELECT COUNT(*) as count FROM inference_results WHERE inference_id = ?
    `).get(inferenceId);
    
    return result ? result.count : 0;
  }

  /**
   * 推論に評価指標を適用
   */
  applyMetricsToInference(inferenceId: string, metrics: Record<string, number>): boolean {
    const inference = this.getInference(inferenceId);
    if (!inference) return false;

    const now = new Date().toISOString();
    const metricsJson = JSON.stringify(metrics);

    this.db.prepare(`
      UPDATE inferences
      SET metrics = ?, updated_at = ?
      WHERE id = ?
    `).run(metricsJson, now, inferenceId);

    return true;
  }

  /**
   * 推論結果に評価指標を適用
   */
  applyMetricsToResult(inferenceId: string, resultId: string, metrics: Record<string, number>): boolean {
    const result = this.getInferenceResult(inferenceId, resultId);
    if (!result) return false;

    const metricsJson = JSON.stringify(metrics);

    this.db.prepare(`
      UPDATE inference_results
      SET metrics = ?
      WHERE id = ? AND inference_id = ?
    `).run(metricsJson, resultId, inferenceId);

    return true;
  }

  /**
   * データベースのレコードをInferenceオブジェクトに変換
   */
  private mapRowToInference(row: any): Inference {
    // プロバイダとモデルの情報を取得（オプション）
    const provider = providersRepository.getProvider(row.provider_id);
    const model = providersRepository.getModel(row.model_id);
    
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      datasetId: row.dataset_id,
      providerId: row.provider_id,
      modelId: row.model_id,
      status: row.status as InferenceStatus,
      progress: row.progress,
      results: [],
      metrics: row.metrics ? JSON.parse(row.metrics) : undefined,
      provider: provider ? {
        name: provider.name,
        type: provider.type
      } : undefined,
      model: model ? {
        name: model.name,
        displayName: model.displayName
      } : undefined,
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at),
      completedAt: row.completed_at ? new Date(row.completed_at) : undefined,
      error: row.error
    };
  }

  /**
   * データベースのレコードをInferenceResultオブジェクトに変換
   */
  private mapRowToInferenceResult(row: any): InferenceResult {
    return {
      id: row.id,
      datasetItemId: row.dataset_item_id,
      input: row.input,
      expectedOutput: row.expected_output,
      actualOutput: row.actual_output,
      metrics: row.metrics ? JSON.parse(row.metrics) : undefined,
      metadata: row.metadata ? JSON.parse(row.metadata) : undefined,
      error: row.error,
      latency: row.latency,
      tokenCount: row.token_count
    };
  }
}

export const inferencesRepository = new InferencesRepository();
