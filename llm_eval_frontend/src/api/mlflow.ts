/**
 * MLflow API クライアント 
 * プロキシ経由でMLflowにアクセスするためのユーティリティ
 */
import axios, { AxiosInstance } from 'axios';

class MLflowClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    // MLflowベースURLは環境変数から取得
    this.baseURL = import.meta.env.VITE_MLFLOW_BASE_URL;
    
    console.log(`MLflow Base URL: ${this.baseURL}`);
    
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // リクエストインターセプター
    this.client.interceptors.request.use(
      (config) => {
        const method = config.method ? config.method.toUpperCase() : 'UNKNOWN';
        console.log(`MLflow Request [${method}] ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // レスポンスインターセプター
    this.client.interceptors.response.use(
      (response) => {
        const method = response.config.method ? response.config.method.toUpperCase() : 'UNKNOWN';
        console.log(`MLflow Response [${method}] ${response.config.url}`);
        return response;
      },
      (error) => {
        if (error.response) {
          console.error('MLflow Error:', error.response.data);
          console.error('Status:', error.response.status);
          error.message = `[${error.response.status}] ${error.response.data?.message || 'MLflow error'}`;
        } else if (error.request) {
          console.error('MLflow Request Error - No response received');
          error.message = 'No response received from MLflow server';
        }
        return Promise.reject(error);
      }
    );
  }

  // エクスペリメント一覧を取得
  async getExperiments() {
    const response = await this.client.get('/ajax-api/2.0/mlflow/experiments/search', {
      params: {
        max_results: 100
      }
    });
    return response.data;
  }

  // 特定のエクスペリメントの実行一覧を取得
  async getRuns(experimentId: string) {
    const response = await this.client.get('/ajax-api/2.0/mlflow/runs/search', {
      params: {
        experiment_ids: [experimentId],
        max_results: 100
      }
    });
    return response.data;
  }

  // 実行の詳細を取得
  async getRun(runId: string) {
    const response = await this.client.get('/ajax-api/2.0/mlflow/runs/get', {
      params: {
        run_id: runId
      }
    });
    return response.data;
  }

  // アーティファクトを取得
  async getArtifact(path: string) {
    try {
      const response = await this.client.get(`/get-artifact?path=${encodeURIComponent(path)}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch artifact:', path, error);
      throw error;
    }
  }

  // MLflowダッシュボードURLを生成
  getDashboardUrl() {
    return this.baseURL;
  }

  // 実行の詳細ページURLを生成
  getRunUrl(runId: string) {
    return `${this.baseURL}/#/experiments/0/runs/${runId}`;
  }
}

// シングルトンインスタンスをエクスポート
export const mlflowClient = new MLflowClient();