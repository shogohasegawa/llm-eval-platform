# 外部Ollamaサービスの設定

このプロジェクトでは、ローカルまたは外部のOllamaサービスと連携することができます。

## 1. ローカルOllamaサービスの使用 (デフォルト設定)

デフォルトでは、docker-composeがOllamaサービスを起動します。この場合、設定は次のようになります：

```yml
# .env ファイル
OLLAMA_BASE_URL=http://ollama:11434
VITE_OLLAMA_BASE_URL=/ollama  # フロントエンドからはプロキシ経由でアクセス
```

## 2. 外部Ollamaサービスの使用 (例: 192.168.3.43で実行)

特定のIPアドレスで実行されている外部Ollamaサービスを使用する場合：

1. **docker-compose.ymlファイルを編集**し、Ollamaサービスをコメントアウトします：

```yml
# docker-compose.yml
services:
  # その他のサービス...

  # ollamaサービスをコメントアウト
  # ollama:
  #   image: ollama/ollama:latest
  #   ports:
  #     - "${OLLAMA_PORT}:11434"
  #   volumes:
  #     - ollama_data:/root/.ollama
  #   restart: unless-stopped
  #   environment:
  #     - OLLAMA_HOST=${OLLAMA_HOST}
  #     - OLLAMA_ORIGINS=${OLLAMA_ORIGINS}
  #     - OLLAMA_MODELS_PATH=${OLLAMA_MODELS_PATH}
  #     - NVIDIA_VISIBLE_DEVICES=all
  #   runtime: nvidia
  #   networks:
  #     - llm-eval-network
  
  # その他のサービス...
```

2. **.envファイルを編集**し、外部Ollamaサービスの接続情報を設定します：

```
# バックエンドからOllamaに接続するURL
OLLAMA_BASE_URL=http://192.168.3.43:11434

# フロントエンドからOllamaへの接続設定
VITE_OLLAMA_BASE_URL=http://192.168.3.43:11434
```

3. 修正した設定でサービスを起動します：

```bash
docker-compose up -d
```

この設定により、APIサーバーとフロントエンドアプリケーションは192.168.3.43で実行されているOllamaサービスに接続します。

## 動作確認方法

外部Ollamaとの接続が正しく設定されているか確認するには：

1. バックエンド接続の確認：
```bash
docker-compose logs api | grep -i ollama
```

2. フロントエンドからモデル一覧を表示して接続を確認
3. Ollamaサービスのログでリクエストを確認：
```bash
# 外部Ollamaサービスのログを確認
ssh user@192.168.3.43 'docker logs ollama'
```

設定に問題がある場合はAPIのログとブラウザのコンソールログを確認してください。