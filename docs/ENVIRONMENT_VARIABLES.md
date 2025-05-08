# 環境変数ガイド

このドキュメントはLLM評価プラットフォームで使用される環境変数について説明します。

## 環境変数ファイル構成

プロジェクトの環境変数は一元化されています：

1. `/.env` - プロジェクトのルートにある統合された環境変数ファイル（すべての設定を含む）
2. `/.env.example` - 環境変数のテンプレート（.envを作成する際の参考用）

**重要**: 環境変数を追加・編集する場合は、ルートディレクトリの`.env`ファイルのみを編集してください。

## 環境変数の読み込み階層

環境変数は以下の優先順位で読み込まれます：

1. コマンドラインで直接設定された環境変数
2. ルートの`.env`ファイル（Docker Composeで読み込まれる）

**重要**: システムはデフォルト値を持たないため、必要な環境変数がすべて`.env`ファイルに設定されていることを確認してください。設定されていない場合、明示的にエラーが発生します。

## 主要なカテゴリと環境変数

### 基本設定

| 変数名 | 説明 | 使用場所 |
|--------|------|---------|
| `LLMEVAL_ENV` | 環境設定（development, production） | 設定クラス、docker-compose.yml |
| `LLMEVAL_LOG_LEVEL` | ログレベル設定 | main.py、設定クラス |
| `LLMEVAL_DB_PATH` | データベースファイルパス | docker-compose.yml |
| `TZ` | タイムゾーン設定 | すべてのコンテナ |

### ネットワーク設定

| 変数名 | 説明 | 使用場所 |
|--------|------|---------|
| `API_PORT` | APIサーバーポート | docker-compose.yml |
| `FRONTEND_PORT` | フロントエンドサーバーポート | docker-compose.yml |
| `MLFLOW_EXTERNAL_PORT` | MLflowサーバー外部ポート | docker-compose.yml |
| `OLLAMA_PORT` | Ollamaサーバーポート | docker-compose.yml |

### フロントエンド設定

| 変数名 | 説明 | 使用場所 |
|--------|------|---------|
| `VITE_API_BASE_URL` | フロントエンド用APIベースURL | client.ts |
| `VITE_OLLAMA_BASE_URL` | Ollamaプロキシパス | proxy-ollama.ts |
| `VITE_MLFLOW_BASE_URL` | MLflowプロキシパス | mlflow.ts |
| `VITE_API_TIMEOUT` | APIリクエストタイムアウト（ミリ秒） | client.ts |
| `VITE_DEBUG_MODE` | デバッグモード | フロントエンド全体 |
| `VITE_APP_NAME` | アプリケーション名 | UI表示 |
| `VITE_APP_VERSION` | アプリケーションバージョン | UI表示 |
| `VITE_LOG_LEVEL` | ログレベル | フロントエンドロギング |

### MLflow設定

| 変数名 | 説明 | 使用場所 |
|--------|------|---------|
| `MLFLOW_HOST` | MLflowホスト名 | docker-compose.yml、main.py |
| `MLFLOW_PORT` | MLflowポート | docker-compose.yml、main.py |
| `MLFLOW_HOST_URI` | MLflowホストURI | docker-compose.yml、proxy.py |
| `LLMEVAL_MLFLOW_EXTERNAL_URI` | 外部アクセス用MLflow URL | プロキシ設定 |

### Ollama設定

| 変数名 | 説明 | 使用場所 |
|--------|------|---------|
| `OLLAMA_BASE_URL` | OllamaベースURL | docker-compose.yml、proxy.py |
| `OLLAMA_HOST` | Ollamaホスト | ollamaコンテナ |
| `OLLAMA_MODELS_PATH` | Ollamaモデル保存パス | ollamaコンテナ |
| `OLLAMA_ORIGINS` | OllamaのCORS設定 | ollamaコンテナ |
| `LLMEVAL_OLLAMA_BASE_URL` | 開発環境でのOllamaサーバーURL | バックエンド設定 |

### バックエンド固有の設定

バックエンド固有の設定変数は `LLMEVAL_` プレフィックスが付いており、Pydanticの`BaseSettings`クラスで自動的に読み込まれます。詳細は`llm_eval_backend/src/app/config/config.py`を参照してください。主な変数には以下のものがあります：

| 変数名 | 説明 |
|--------|------|
| `LLMEVAL_DATASET_DIR` | テスト用データセットのパス |
| `LLMEVAL_TRAIN_DIR` | n-shot用データセットのパス |
| `LLMEVAL_RESULTS_DIR` | 結果保存ディレクトリ |
| `LLMEVAL_DEFAULT_MAX_TOKENS` | 生成するトークンの最大数 |
| `LLMEVAL_DEFAULT_TEMPERATURE` | 生成時の温度パラメータ |
| `LLMEVAL_MODEL_TIMEOUT` | モデル呼び出しのタイムアウト時間 |
| `LLMEVAL_BATCH_SIZE` | バッチ処理サイズ |

### フロントエンド固有の設定

フロントエンドの環境変数は必ず`VITE_`プレフィックスを付ける必要があります。これはViteのセキュリティ制限であり、`VITE_`プレフィックスのない変数はフロントエンドコードからアクセスできません。

## 環境変数管理のベストプラクティス

### 新しい環境変数の追加

1. ルートの`.env`ファイルと`.env.example`ファイルの両方に追加する
2. 適切なカテゴリに配置し、詳細なコメントを追加する
3. 環境変数ドキュメント（このファイル）も更新する

### バックエンド変数

1. 設定クラスで使用する変数は必ず`LLMEVAL_`プレフィックスを付ける
2. `LLMEVAL_`プレフィックスのついた変数は、`config.py`の`Settings`クラスのフィールドとして定義すると自動的に読み込まれる

### フロントエンド変数

1. フロントエンド用の変数は必ず`VITE_`プレフィックスが必要
2. 機密情報（APIキーなど）はフロントエンド用の環境変数に設定しない
3. フロントエンドの環境変数はビルド時に埋め込まれる静的な値として扱われる

### 接続変数

1. サービス間接続のURLは一貫した命名規則を使用する
2. すべての必要な変数が`.env`ファイルに定義されていることを確認する（デフォルト値は使用しない）
3. 未設定の場合にシステムがエラーを明示的に表示するため、問題の早期発見が可能

## 環境変数使用場所のまとめ

主な環境変数が使用される場所：

1. **docker-compose.yml** - コンテナの環境設定と接続情報
2. **main.py** - FastAPIサーバーの設定とプロキシルート
3. **proxy.py, ollama_manager.py** - 各サービスへの接続設定
4. **client.ts, mlflow.ts, proxy-ollama.ts** - フロントエンドの接続設定
5. **config.py** - バックエンド設定クラス（`LLMEVAL_`プレフィックスの変数を自動読み込み）