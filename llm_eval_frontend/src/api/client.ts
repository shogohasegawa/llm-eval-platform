import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

/**
 * APIクライアントの設定
 */
class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    // バックエンドAPIのURL
    // ホスト名は実行環境に合わせて決める
    // ブラウザからアクセスするため、外部からアクセス可能なホスト名/ポートが必要
    
    // コンテナ名でのアクセスは不可能（ブラウザからはコンテナネットワークにアクセスできない）
    // docker-compose.yml の port マッピングを使ってアクセスする必要がある
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
    console.log(`API Base URL: ${this.baseURL}, Environment: ${import.meta.env.MODE}`);
    console.log(`Environment variables:`, import.meta.env);
    
    // バックエンドが利用可能かどうかをチェック
    fetch(`${this.baseURL}/api/v1/metrics/available`)
      .then(response => {
        if (!response.ok) {
          console.error('APIサーバーの応答が正常でありません:', response.status);
        } else {
          console.log('APIサーバーと接続できました');
        }
      })
      .catch(error => {
        console.error('APIサーバーへの接続エラー:', error);
      });
    
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      // リクエストタイムアウト設定（.envから設定を読み込み、デフォルトは30秒）
      timeout: import.meta.env.VITE_API_TIMEOUT ? parseInt(import.meta.env.VITE_API_TIMEOUT) : 30000,
    });

    // リクエストインターセプター
    this.client.interceptors.request.use(
      (config) => {
        const method = config.method ? config.method.toUpperCase() : 'UNKNOWN';
        console.log(`API Request [${method}] ${config.url}`);
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
        console.log(`API Response [${method}] ${response.config.url}:`, response.data);
        
        // デバッグ情報を追加
        if (typeof response.data === 'object' && response.data !== null) {
          console.log('Response data type:', typeof response.data);
          console.log('Response data keys:', Object.keys(response.data));
          console.log('Response data nested types:', 
            Object.entries(response.data).map(([key, value]) => 
              `${key}: ${typeof value}${Array.isArray(value) ? ` (Array[${(value as any[]).length}])` : ''}`
            )
          );
        }
        
        return response;
      },
      (error) => {
        // エラーハンドリング
        if (error.response) {
          // サーバーからのレスポンスがある場合
          const method = error.config && error.config.method ? error.config.method.toUpperCase() : 'UNKNOWN';
          const url = error.config ? error.config.url : 'UNKNOWN';
          console.error(`API Error [${method}] ${url}:`, error.response.data);
          console.error('Status:', error.response.status);
          console.error('Headers:', error.response.headers);
          
          // エラーメッセージをわかりやすく拡張
          if (error.response.data && error.response.data.detail) {
            error.message = `[${error.response.status}] ${error.response.data.detail}`;
          }
        } else if (error.request) {
          // リクエストは送信されたがレスポンスがない場合
          console.error('API Request Error:', error.request);
          console.error('No response received. Check if the server is running.');
          error.message = 'サーバーからの応答がありません。サーバーが実行中か確認してください。';
        } else {
          // リクエスト設定中にエラーが発生した場合
          console.error('API Config Error:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  // GETリクエスト
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  // POSTリクエスト
  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  // PUTリクエスト
  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  // DELETEリクエスト
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  // Blobリクエスト (ファイルダウンロード用)
  async getBlob(url: string, config?: AxiosRequestConfig): Promise<Blob> {
    const response = await this.client.get(url, {
      ...config,
      responseType: 'blob'
    });
    return response.data;
  }
}

// シングルトンインスタンスをエクスポート
export const apiClient = new ApiClient();
