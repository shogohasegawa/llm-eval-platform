import { v4 as uuidv4 } from 'uuid';
import DatabaseManager from './database';
import { 
  Metric, 
  MetricFormData, 
  MetricType, 
  LeaderboardEntry, 
  LeaderboardFilterOptions 
} from '../types/metrics';
import { inferencesRepository } from './inferences.repository';

/**
 * 評価指標リポジトリクラス
 * SQLiteデータベースとのやり取りを担当
 */
export class MetricsRepository {
  private db = DatabaseManager.getInstance().getDb();

  /**
   * 全評価指標を取得
   */
  getMetrics(): Metric[] {
    const rows = this.db.prepare(`
      SELECT id, name, type, description, is_higher_better, parameters, created_at, updated_at
      FROM metrics
      ORDER BY created_at DESC
    `).all();

    return rows.map(row => this.mapRowToMetric(row));
  }

  /**
   * 特定の評価指標を取得
   */
  getMetric(id: string): Metric | null {
    const row = this.db.prepare(`
      SELECT id, name, type, description, is_higher_better, parameters, created_at, updated_at
      FROM metrics
      WHERE id = ?
    `).get(id);

    if (!row) return null;
    return this.mapRowToMetric(row);
  }

  /**
   * 評価指標を作成
   */
  createMetric(data: MetricFormData): Metric {
    const id = uuidv4();
    const now = new Date().toISOString();
    const parameters = data.parameters ? JSON.stringify(data.parameters) : null;

    this.db.prepare(`
      INSERT INTO metrics (id, name, type, description, is_higher_better, parameters, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      data.name,
      data.type,
      data.description || null,
      data.isHigherBetter ? 1 : 0,
      parameters,
      now,
      now
    );

    return {
      id,
      name: data.name,
      type: data.type as MetricType,
      description: data.description,
      isHigherBetter: data.isHigherBetter,
      parameters: data.parameters,
      createdAt: new Date(now),
      updatedAt: new Date(now)
    };
  }

  /**
   * 評価指標を更新
   */
  updateMetric(id: string, data: MetricFormData): Metric | null {
    const metric = this.getMetric(id);
    if (!metric) return null;

    const now = new Date().toISOString();
    const parameters = data.parameters ? JSON.stringify(data.parameters) : null;

    this.db.prepare(`
      UPDATE metrics
      SET name = ?, type = ?, description = ?, is_higher_better = ?, parameters = ?, updated_at = ?
      WHERE id = ?
    `).run(
      data.name,
      data.type,
      data.description || null,
      data.isHigherBetter ? 1 : 0,
      parameters,
      now,
      id
    );

    return {
      ...metric,
      name: data.name,
      type: data.type as MetricType,
      description: data.description,
      isHigherBetter: data.isHigherBetter,
      parameters: data.parameters,
      updatedAt: new Date(now)
    };
  }

  /**
   * 評価指標を削除
   */
  deleteMetric(id: string): boolean {
    const result = this.db.prepare(`
      DELETE FROM metrics WHERE id = ?
    `).run(id);

    return result.changes > 0;
  }

  /**
   * リーダーボードのデータを取得
   */
  getLeaderboard(filters?: LeaderboardFilterOptions): LeaderboardEntry[] {
    // 推論の結果に基づいてリーダーボードデータを生成
    const inferences = inferencesRepository.getInferences({
      status: 'completed',
      ...(filters ? {
        datasetId: filters.datasetId,
        providerId: filters.providerId,
        modelId: filters.modelId
      } : {})
    });

    if (!inferences.length) return [];

    // メトリクスが設定されている推論のみを対象にする
    const inferenceWithMetrics = inferences.filter(inf => inf.metrics && Object.keys(inf.metrics).length > 0);
    
    // 主要メトリクスを特定（フィルタリングまたはデフォルト）
    let primaryMetricId = filters?.metricId;
    
    if (!primaryMetricId && inferenceWithMetrics.length > 0) {
      // デフォルトのメトリクスを最初の推論から取得
      const firstInfMetrics = inferenceWithMetrics[0].metrics;
      if (firstInfMetrics) {
        primaryMetricId = Object.keys(firstInfMetrics)[0];
      }
    }
    
    if (!primaryMetricId) return [];
    
    // メトリクス情報を取得（高いほうが良いかどうか）
    const primaryMetric = this.getMetric(primaryMetricId);
    const isHigherBetter = primaryMetric?.isHigherBetter ?? true;
    
    // リーダーボードエントリを作成して並べ替え
    let entries = inferenceWithMetrics
      .filter(inf => inf.metrics && inf.metrics[primaryMetricId!] !== undefined)
      .map(inference => {
        return {
          rank: 0, // 後で計算
          inferenceId: inference.id,
          inferenceName: inference.name,
          providerId: inference.providerId,
          providerName: inference.provider?.name || 'Unknown Provider',
          modelId: inference.modelId,
          modelName: inference.model?.displayName || inference.model?.name || 'Unknown Model',
          datasetId: inference.datasetId,
          datasetName: 'Dataset', // データセット名は別途取得する必要あり
          metrics: inference.metrics!,
          createdAt: inference.createdAt
        };
      });
    
    // スコアに基づいて並べ替え
    entries.sort((a, b) => {
      const scoreA = a.metrics[primaryMetricId!];
      const scoreB = b.metrics[primaryMetricId!];
      return isHigherBetter ? scoreB - scoreA : scoreA - scoreB;
    });
    
    // ランクを割り当て
    entries = entries.map((entry, index) => ({
      ...entry,
      rank: index + 1
    }));
    
    // 件数制限
    if (filters?.limit && filters.limit > 0 && filters.limit < entries.length) {
      entries = entries.slice(0, filters.limit);
    }
    
    return entries;
  }

  /**
   * メトリクスを計算して推論に適用する
   */
  calculateAndApplyMetrics(inferenceId: string): Record<string, number> | null {
    const inference = inferencesRepository.getInference(inferenceId);
    if (!inference || inference.status !== 'completed' || !inference.results.length) {
      return null;
    }

    const metrics: Record<string, number> = {};
    
    // 正確性メトリクス（exact_match）
    if (inference.results.some(r => r.expectedOutput)) {
      let exactMatches = 0;
      let totalWithExpected = 0;
      
      for (const result of inference.results) {
        if (result.expectedOutput) {
          totalWithExpected++;
          if (result.actualOutput.trim() === result.expectedOutput.trim()) {
            exactMatches++;
          }
        }
      }
      
      if (totalWithExpected > 0) {
        metrics['exact_match'] = (exactMatches / totalWithExpected) * 100;
      }
    }
    
    // レイテンシメトリクス
    if (inference.results.some(r => r.latency !== undefined)) {
      const latencies = inference.results.map(r => r.latency).filter(l => l !== undefined) as number[];
      if (latencies.length > 0) {
        const avgLatency = latencies.reduce((sum, val) => sum + val, 0) / latencies.length;
        metrics['avg_latency'] = avgLatency;
      }
    }
    
    // トークン数メトリクス
    if (inference.results.some(r => r.tokenCount !== undefined)) {
      const tokenCounts = inference.results.map(r => r.tokenCount).filter(t => t !== undefined) as number[];
      if (tokenCounts.length > 0) {
        const avgTokens = tokenCounts.reduce((sum, val) => sum + val, 0) / tokenCounts.length;
        metrics['avg_tokens'] = avgTokens;
      }
    }
    
    // メトリクスを推論に適用
    if (Object.keys(metrics).length > 0) {
      inferencesRepository.applyMetricsToInference(inferenceId, metrics);
    }
    
    return metrics;
  }

  /**
   * データベースのレコードをMetricオブジェクトに変換
   */
  private mapRowToMetric(row: any): Metric {
    return {
      id: row.id,
      name: row.name,
      type: row.type as MetricType,
      description: row.description,
      isHigherBetter: Boolean(row.is_higher_better),
      parameters: row.parameters ? JSON.parse(row.parameters) : undefined,
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at)
    };
  }
}

export const metricsRepository = new MetricsRepository();
