# LLM Evaluation Backend

LLM Evaluation Backendは、大規模言語モデル（LLM）の評価を効率的に実行するためのバックエンドサービスです。APIを通じて複数のデータセットでモデルを評価し、様々なメトリクスでパフォーマンスを測定できます。

## 📋 目次

- [機能概要](#機能概要)
- [クイックスタート](#クイックスタート)
- [詳細インストール手順](#詳細インストール手順)
- [環境設定](#環境設定)
- [使用方法](#使用方法)
  - [サーバー起動](#サーバー起動)
  - [APIリクエスト例](#apiリクエスト例)
  - [APIエンドポイント一覧](#apiエンドポイント一覧)
- [Dockerでの実行](#dockerでの実行)
- [データセット](#データセット)
  - [対応データセット](#対応データセット)
  - [データセット形式](#データセット形式)
  - [データセットの追加方法](#データセットの追加方法)
- [評価メトリクス](#評価メトリクス)
- [トラブルシューティング](#トラブルシューティング)

## 機能概要

- **複数データセット評価**: 複数の標準データセットを使用してモデルを包括的に評価
- **Few-shot学習のサポート**: 0-shot、Few-shotでの評価に対応
- **多様なメトリクス**: 文字ベースF1、完全一致、含有率など複数の評価指標
- **REST API**: FastAPIを使用した高速なAPIインターフェース
- **マルチプロバイダー対応**: OpenAI、Anthropic、Ollamaなど複数のLLMプロバイダーに対応
- **フォールバック機能**: 特定のプロバイダーが使用できない場合に代替プロバイダーを使用
- **MLflow連携**: 評価結果の追跡と可視化
- **Docker対応**: コンテナ化による簡単なデプロイと実行

## クイックスタート

```bash
# リポジトリのクローン
git clone https://github.com/shogohasegawa/llm_eval_backend.git
cd llm_eval_backend

# 依存関係のインストール
uv init
uv sync

# サーバー起動
uv run src/app/main.py
```

サーバーが起動したら、ブラウザで http://localhost:8000/docs にアクセスしてSwagger UIからAPIを確認・テストできます。

## 詳細インストール手順

### 前提条件

- Python 3.11以上
- uv (パッケージマネージャ)
- Ollama（ローカルでモデルを実行する場合）

### インストール手順

1. リポジトリをクローンする

```bash
git clone https://github.com/shogohasegawa/llm_eval_backend.git
cd llm_eval_backend
```

2. 仮想環境を作成し、依存関係をインストール

```bash
uv init
uv sync
```

3. 環境設定ファイルを作成

```bash
cp .env.sample .env
# .envファイルを編集して環境に合わせた設定を行う
```

## 環境設定

`.env`ファイルまたは環境変数で以下の設定が可能です。主要な設定項目は：

| 設定項目 | 説明 | デフォルト値 |
|---------|------|------------|
| `LLMEVAL_DATASET_DIR` | 評価データセットのディレクトリパス | `/path/to/datasets/test` |
| `LLMEVAL_TRAIN_DIR` | Few-shot用学習データセットのディレクトリパス | `/path/to/datasets/train` |
| `LLMEVAL_RESULTS_DIR` | 評価結果の保存先ディレクトリ | `/app/results` |
| `LLMEVAL_LITELLM_BASE_URL` | Ollama APIのベースURL | `http://localhost:11434/api/generate` |
| `LLMEVAL_OPENAI_API_KEY` | OpenAI APIキー | - |
| `LLMEVAL_ANTHROPIC_API_KEY` | Anthropic APIキー | - |
| `LLMEVAL_DEFAULT_PROVIDER` | デフォルトのプロバイダー | `ollama` |
| `LLMEVAL_FALLBACK_PROVIDERS` | フォールバックプロバイダーリスト | `[]` |
| `LLMEVAL_ENABLE_LITELLM_CACHE` | LiteLLMキャッシュの有効化 | `true` |

より詳しい設定オプションは[.env.sample](.env.sample)ファイルを参照してください。

## 使用方法

### サーバー起動

開発環境での起動：

```bash
# 開発モードで起動（コード変更時自動リロード）
uv run src/app/main.py
```

本番環境での起動：

```bash
# 本番環境用設定でuvicornを直接実行
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### APIリクエスト例

#### 評価実行リクエスト

```bash
curl -X POST "http://localhost:8000/api/evaluation/run" \
     -H "Content-Type: application/json" \
     -d '{
       "datasets": ["aio", "janli"],
       "num_samples": 10,
       "n_shots": [0, 2],
       "model": {
         "provider": "ollama",
         "model_name": "llama3:latest",
         "max_tokens": 1024,
         "temperature": 0.0,
         "top_p": 1.0,
         "additional_params": {}
       }
     }'
```

#### レスポンス例

```json
{
  "model_info": {
    "provider": "ollama",
    "model_name": "llama3:latest",
    "max_tokens": 1024,
    "temperature": 0.0,
    "top_p": 1.0,
    "additional_params": {}
  },
  "metrics": {
    "aio_0shot_char_f1": 0.78,
    "aio_0shot_exact_match": 0.35,
    "aio_0shot_exact_match_error_rate": 0.0,
    "aio_2shot_char_f1": 0.82,
    "aio_2shot_exact_match": 0.41,
    "aio_2shot_exact_match_error_rate": 0.0,
    "janli_0shot_char_f1": 0.65,
    "janli_0shot_exact_match": 0.30,
    "janli_0shot_exact_match_error_rate": 0.0,
    "janli_2shot_char_f1": 0.70,
    "janli_2shot_exact_match": 0.33,
    "janli_2shot_exact_match_error_rate": 0.0
  }
}
```

### APIエンドポイント一覧

#### 評価関連

- **POST /api/evaluation/run** - モデル評価の実行

#### モデル管理関連

- **GET /api/models/providers** - 利用可能なプロバイダー一覧の取得
- **GET /api/models/models/{provider_name}** - 特定プロバイダーの利用可能モデル一覧
- **GET /api/models/models** - 全プロバイダーの利用可能モデル一覧
- **GET /api/models/check/{provider_name}/{model_name}** - モデルの利用可能性チェック
- **POST /api/models/download/ollama/{model_name}** - Ollamaモデルのダウンロード
- **GET /api/models/info/{provider_name}/{model_name}** - モデル情報の取得

## Dockerでの実行

### 単独でのDockerビルドと実行

```bash
# イメージのビルド
docker build -t llm-eval-backend .

# 基本的な実行
docker run -p 8000:8000 llm-eval-backend

# ボリュームマウントと環境変数を指定した実行
docker run -p 8000:8000 \
  -v $(pwd)/datasets:/app/datasets \
  -v $(pwd)/results:/app/results \
  -e LLMEVAL_DATASET_DIR=/app/datasets/test \
  -e LLMEVAL_TRAIN_DIR=/app/datasets/train \
  -e LLMEVAL_RESULTS_DIR=/app/results \
  -e LLMEVAL_LITELLM_BASE_URL=http://host.docker.internal:11434/api/generate \
  llm-eval-backend
```

### Docker Composeでの実行

docker-compose.ymlファイルがある場合：

```bash
# 環境設定
cp .env.sample .env
# 必要に応じて.envファイルを編集

# 起動
docker-compose up -d

# ログ確認
docker-compose logs -f api
```

詳細な Docker 設定については [DOCKER.md](DOCKER.md) を参照してください。

## データセット

### 対応データセット

デフォルトで以下のデータセットに対応しています：

- **JASTER** - 日本語の要約、翻訳、エンティティ認識などのタスクを含む総合的なデータセット

### データセット形式

データセットは以下のJSON形式で作成します：

```json
{
  "instruction": "タスクの指示文",
  "metrics": ["char_f1", "exact_match"],
  "output_length": 1024,
  "samples": [
    {
      "input": "入力テキスト",
      "output": "正解出力"
    },
    ...
  ]
}
```

### データセットの追加方法

1. 上記のフォーマットに従ったJSONファイルを作成
2. ファイルを設定した`LLMEVAL_DATASET_DIR`ディレクトリに配置（例：`your_dataset.json`）
3. Few-shotテスト用に、同じ形式のファイルを`LLMEVAL_TRAIN_DIR`にも配置
4. APIリクエスト時にデータセット名として指定（例：`"datasets": ["your_dataset"]`）

## 評価メトリクス

システムは以下のメトリクスをサポートしています：

- **char_f1**: 文字ベースのF1スコア（fuzzywuzzyを使用）
- **exact_match**: 予測と正解の完全一致率
- **exact_match_figure**: 図やデータを含む問題の完全一致率
- **contains_answer**: 正解が出力に含まれているかどうか
- **set_f1**: 集合ベースのF1スコア（予測と正解を集合として扱う）
- **bleu**: BLEU機械翻訳評価スコア

カスタムメトリクスを追加するには、`src/app/metrics`ディレクトリに新しいメトリクスクラスを作成し、基底クラス`BaseMetric`を継承して実装します。

## トラブルシューティング

### よくある問題と解決策

**問題**: Ollamaモデルに接続できない
**解決策**:
1. Ollamaサーバーが実行中であることを確認
2. `.env`ファイルの`LLMEVAL_LITELLM_BASE_URL`が正しいことを確認
3. Dockerで実行している場合は`host.docker.internal`を使用してホストマシンのOllamaにアクセス

**問題**: 評価実行時にAPI呼び出しエラーが発生する
**解決策**:
1. モデルがダウンロード済みかチェック: `GET /api/models/check/{provider}/{model}`
2. 必要ならモデルをダウンロード: `POST /api/models/download/ollama/{model}`
3. API呼び出しのタイムアウト設定を`.env`ファイルの`LLMEVAL_MODEL_TIMEOUT`で調整

**問題**: データセットが見つからないエラー
**解決策**:
1. `LLMEVAL_DATASET_DIR`と`LLMEVAL_TRAIN_DIR`のパスが正しいことを確認
2. データセットファイルが正しいJSON形式であることを確認
3. データセット名にタイプミスがないことを確認（ファイル名から`.json`拡張子を除いた名前を使用）
