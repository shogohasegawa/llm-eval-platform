/**
 * Ollamaサーバーの直接アクセス用プロキシクライアント
 * バックエンドAPIを経由してOllamaサーバーと通信します
 */

// OllamaのAPIレスポンス型定義
interface OllamaGenerateResponse {
  model: string;
  created_at: string;
  response: string;
  done: boolean;
  context?: number[];
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
  prompt_eval_duration?: number;
  eval_count?: number;
  eval_duration?: number;
}

interface OllamaGenerateRequest {
  model: string;
  prompt: string;
  system?: string;
  template?: string;
  context?: number[];
  stream?: boolean;
  raw?: boolean;
  format?: string;
  options?: {
    num_predict?: number;
    temperature?: number;
    top_k?: number;
    top_p?: number;
    stop?: string[];
    mirostat?: number;
  };
}

interface OllamaTagsResponse {
  models: OllamaModelInfo[];
}

interface OllamaModelInfo {
  name: string;
  model: string;
  modified_at: string;
  size: number;
  digest: string;
  details: {
    parent_model?: string;
    format?: string;
    family?: string;
    families?: string[];
    parameter_size?: string;
    quantization_level?: string;
  };
}

/**
 * Ollama API プロキシクライアント
 * バックエンドプロキシを経由してOllamaサーバーにアクセス
 */
export const ollamaDirectApi = {
  /**
   * テキスト生成（completion）
   * @param options リクエスト設定
   * @returns 生成されたテキストレスポンス
   */
  generateCompletion: async (options: OllamaGenerateRequest): Promise<OllamaGenerateResponse> => {
    // プロキシURL（環境変数から取得）
    const ollamaBaseUrl = import.meta.env.VITE_OLLAMA_BASE_URL;
    const url = `${ollamaBaseUrl}/api/generate`;
    
    console.log(`Requesting Ollama completion via proxy: ${url}`);
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(options),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Ollama API error: ${response.status} ${response.statusText}\n${errorText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error accessing Ollama API:', error);
      throw error;
    }
  },
  
  /**
   * 利用可能なモデル一覧を取得
   * @returns モデル情報の配列
   */
  getModels: async (): Promise<OllamaModelInfo[]> => {
    const ollamaBaseUrl = import.meta.env.VITE_OLLAMA_BASE_URL;
    const url = `${ollamaBaseUrl}/api/tags`;
    
    console.log(`Requesting Ollama models via proxy: ${url}`);
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Ollama API error: ${response.status} ${response.statusText}\n${errorText}`);
      }
      
      const data: OllamaTagsResponse = await response.json();
      return data.models || [];
    } catch (error) {
      console.error('Error fetching Ollama models:', error);
      throw error;
    }
  },
  
  /**
   * ストリーミングテキスト生成
   * @param options リクエスト設定
   * @param onChunk チャンク受信時のコールバック
   * @param onDone 完了時のコールバック
   * @param onError エラー発生時のコールバック
   */
  streamingGenerate: async (
    options: OllamaGenerateRequest,
    onChunk: (chunk: OllamaGenerateResponse) => void,
    onDone: (fullResponse: OllamaGenerateResponse) => void,
    onError: (error: Error) => void
  ): Promise<void> => {
    const ollamaBaseUrl = import.meta.env.VITE_OLLAMA_BASE_URL;
    const url = `${ollamaBaseUrl}/api/generate`;
    
    console.log(`Requesting Ollama streaming completion via proxy: ${url}`);
    
    try {
      // ストリーミングを有効化
      const streamOptions = {
        ...options,
        stream: true
      };
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(streamOptions),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Ollama API error: ${response.status} ${response.statusText}\n${errorText}`);
      }
      
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }
      
      let completeResponse = '';
      let fullResponse: OllamaGenerateResponse | null = null;
      
      // レスポンスを処理するループ
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
        // バイナリデータをテキストに変換
        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');
        
        for (const line of lines) {
          try {
            const json = JSON.parse(line);
            completeResponse += json.response;
            onChunk(json);
            
            if (json.done) {
              fullResponse = json;
            }
          } catch (e) {
            console.warn('Failed to parse JSON from chunk:', line);
          }
        }
      }
      
      // 完了コールバックを呼び出し
      if (fullResponse) {
        // 完全なレスポンステキストを設定
        fullResponse.response = completeResponse;
        onDone(fullResponse);
      } else {
        // フォールバック
        onDone({
          model: options.model,
          created_at: new Date().toISOString(),
          response: completeResponse,
          done: true
        });
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      console.error('Error in Ollama streaming:', err);
      onError(err);
    }
  }
};

export default ollamaDirectApi;