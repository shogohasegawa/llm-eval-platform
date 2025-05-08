# 環境変数ガイド

このドキュメントはLLM評価プラットフォームで使用される環境変数について説明します。

## 環境変数ファイル構成

プロジェクトには複数の環境変数ファイルが存在します：

1. `/.env` - プロジェクトのルートにある主要な環境変数ファイル
2. `/.env.example` - 環境変数のテンプレート
3. `/llm_eval_backend/.env` - バックエンド固有の環境変数
4. `/llm_eval_backend/.env.sample` - バックエンド環境変数のテンプレート

## 環境変数の読み込み階層

環境変数は以下の優先順位で読み込まれます：

1. コマンドラインで直接設定された環境変数
2. ローカルの`.env`ファイル
3. デフォルト値

## 主要なカテゴリと環境変数

### 基本設定

| 変数名 | デフォルト値 | 説明 | 使用場所 |
|--------|------------|------|---------|
| `LLMEVAL_ENV` | `production` | 環境設定（development, production） | 設定クラス、docker-compose.yml |
| `LLMEVAL_LOG_LEVEL` | `INFO` | ログレベル設定 | main.py、設定クラス |
| `LLMEVAL_DB_PATH` | `/external_data/llm_eval.db` | データベースファイルパス | docker-compose.yml |
| `TZ` | `Asia/Tokyo` | タイムゾーン設定 | すべてのコンテナ |

### ネットワーク設定

| 変数名 | デフォルト値 | 説明 | 使用場所 |
|--------|------------|------|---------|
| `API_PORT` | `8001` | APIサーバーポート | docker-compose.yml |
| `FRONTEND_PORT` | `4173` | フロントエンドサーバーポート | docker-compose.yml |
| `MLFLOW_EXTERNAL_PORT` | `5000` | MLflowサーバー外部ポート | docker-compose.yml |
| `OLLAMA_PORT` | `11434` | Ollamaサーバーポート | docker-compose.yml |

### フロントエンド設定

| 変数名 | デフォルト値 | 説明 | 使用場所 |
|--------|------------|------|---------|
| `VITE_API_BASE_URL` | `` (空) | フロントエンド用APIベースURL | client.ts |
| `VITE_OLLAMA_BASE_URL` | `/ollama` | Ollamaプロキシパス | proxy-ollama.ts |
| `VITE_MLFLOW_BASE_URL` | `/mlflow` | MLflowプロキシパス | mlflow.ts |

### MLflow設定

| 変数名 | デフォルト値 | 説明 | 使用場所 |
|--------|------------|------|---------|
| `MLFLOW_HOST` | `mlflow` | MLflowホスト名 | docker-compose.yml、main.py |
| `MLFLOW_PORT` | `5000` | MLflowポート | docker-compose.yml、main.py |
| `MLFLOW_HOST_URI` | `http://mlflow:5000` | MLflowホストURI | docker-compose.yml、proxy.py |
| `LLMEVAL_MLFLOW_TRACKING_URI` | `http://mlflow:5000` | コンテナ間通信用MLflowトラッキングURI | 設定クラス |
| `LLMEVAL_MLFLOW_EXTERNAL_URI` | サーバーIPアドレス | 外部アクセス用MLflow URL | プロキシ設定 |

### Ollama設定

| 変数名 | デフォルト値 | 説明 | 使用場所 |
|--------|------------|------|---------|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | OllamaベースURL | docker-compose.yml、ollama_manager.py、main.py |
| `OLLAMA_HOST` | `0.0.0.0` | Ollamaホスト | ollamaコンテナ |
| `OLLAMA_MODELS_PATH` | `/root/.ollama` | Ollamaモデル保存パス | ollamaコンテナ |
| `OLLAMA_ORIGINS` | `*` | OllamaのCORS設定 | ollamaコンテナ |
| `LLMEVAL_OLLAMA_BASE_URL` | サーバーIPアドレス | 開発環境でのOllamaサーバーURL | バックエンド設定 |

### バックエンド固有の設定

バックエンド固有の設定変数は `LLMEVAL_` プレフィックスが付いており、Pydanticの`BaseSettings`クラスで自動的に読み込まれます。詳細は`llm_eval_backend/src/app/config/config.py`を参照してください。

## 環境変数の追加・変更時の注意点

1. 新しい環境変数を追加する場合は、`.env.example`と対応するドキュメントも更新してください
2. `LLMEVAL_`プレフィックスの変数はバックエンドの設定クラスに自動的に読み込まれます
3. サービス間接続用の変数（MLFLOW_HOST, OLLAMA_BASE_URLなど）はdocker-compose.ymlとプロキシコードで直接参照されています
4. フロントエンド用の変数は`VITE_`プレフィックスが必要です

## 環境変数使用場所のまとめ

主な環境変数が使用される場所：

1. **docker-compose.yml** - コンテナの環境設定と接続情報
2. **main.py** - FastAPIサーバーの設定とプロキシルート
3. **proxy.py, ollama_manager.py** - 各サービスへの接続設定
4. **client.ts, mlflow.ts, proxy-ollama.ts** - フロントエンドの接続設定
5. **config.py** - バックエンド設定クラス（`LLMEVAL_`プレフィックスの変数を自動読み込み）