import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

/**
 * APIクライアントの設定
 */
class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    // バックエンドAPIのURL
    // 開発環境ではプロキシを使用するため、相対パスで設定
    this.baseURL = '';
    
    this.client = axios.create({
      headers: {
        'Content-Type': 'application/json',
      },
      // リクエストタイムアウト設定（30秒）
      timeout: 30000,
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
        } else if (error.request) {
          // リクエストは送信されたがレスポンスがない場合
          console.error('API Request Error:', error.request);
          console.error('No response received. Check if the server is running.');
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
