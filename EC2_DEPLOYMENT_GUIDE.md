# EC2 分散デプロイメントガイド

このガイドでは、LLM評価プラットフォームを以下の分散構成でEC2インスタンスにデプロイする方法を説明します：
- CPUインスタンス：フロントエンド、APIバックエンド、MLflow
- GPUインスタンス：Ollama LLMサービス

## アーキテクチャの概要

```
┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│          CPUインスタンス         │      │          GPUインスタンス         │
│                                 │      │                                 │
│  ┌─────────┐  ┌─────┐  ┌─────┐  │      │  ┌────────┐                     │
│  │フロントエンド│  │ API │  │MLflow│  │      │  │ Ollama │                    │
│  │  (Vue)  ├──┤(Fast├──┤Server│  │      │  │ Server │                    │
│  │         │  │ API)│  │     │  │      │  │        │                    │
│  └─────────┘  └─────┘  └─────┘  │      │  └────────┘                    │
│                                 │      │                                 │
└──────────────┬──────────────────┘      └──────────────┬──────────────────┘
               │                                        │
               │         ネットワーク                     │
               └────────────────────────────────────────┘
```

## デプロイメントオプション

このプロジェクトは以下の3つのデプロイメントオプションをサポートしています：

1. **分散デプロイメント**（推奨）：
   - CPUインスタンス：フロントエンド、API、MLflow
   - GPUインスタンス：Ollama
   - 設定ファイル：`docker-compose.cpu.yml`と`docker-compose.gpu.yml`

2. **単一サーバーデプロイメント**：
   - すべてのサービスを1台のサーバーで実行
   - 設定ファイル：`docker-compose.full.yml`
   - GPU対応マシンの場合はGPUを使用（GPU設定をコメントアウトすればCPUのみでも動作）

## 事前準備

- EC2インスタンス：
  - CPUインスタンス（例：t3.xlarge）：フロントエンド、API、MLflow用
  - GPUインスタンス（例：g4dn.xlarge）：Ollama用
- 両インスタンスにDockerとDocker Composeをインストール
- GPUインスタンスにはNVIDIAドライバとDockerのGPUサポートをインストール
- 以下のポートを許可するようにセキュリティグループを設定：
  - ポート4173（フロントエンド）
  - ポート8001（API）
  - ポート5000（MLflow）
  - ポート11434（Ollama）

## ステップ1：両インスタンスにリポジトリをクローン

```bash
git clone https://github.com/your-repo/llm-eval-platform.git
cd llm-eval-platform
```

## ステップ2：CPUインスタンスのセットアップ

1. 環境設定ファイルを作成：

```bash
# 設定ファイルの例をコピー
cp .env.cpu.example .env

# 実際のGPUインスタンスIPで.envファイルを編集
nano .env
```

2. CPUインスタンスのコンポーネントを実行：

```bash
docker-compose -f docker-compose.cpu.yml up -d
```

これにより以下が起動します：
- フロントエンド（ポート4173）
- API（ポート8001）
- MLflow（ポート5000）

## ステップ3：GPUインスタンスのセットアップ

1. 環境設定ファイルを作成：

```bash
# 設定ファイルの例をコピー
cp .env.gpu.example .env

# 必要に応じて.envファイルを編集
nano .env
```

2. GPUインスタンスでOllamaを実行：

```bash
docker-compose -f docker-compose.gpu.yml up -d
```

これにより以下が起動します：
- GPU対応のOllama（ポート11434）

## ステップ4：接続の確認

1. GPUインスタンス上のOllamaがCPUインスタンスからアクセス可能か確認：

```bash
# CPUインスタンスから実行
curl http://<gpu-instance-ip>:11434/api/tags
```

2. APIがOllamaに到達できるか確認：

```bash
# CPUインスタンスから実行
curl http://localhost:8001/api/v1/ollama/models
```

3. ブラウザからフロントエンドにアクセス：

```
http://<cpu-instance-ip>:4173
```

## 単一サーバーでのデプロイメント

すべてのサービスを1台のサーバー（できればGPU搭載）で実行する場合：

1. 環境設定ファイルを作成：

```bash
cp .env.full.example .env
```

2. すべてのサービスを起動：

```bash
docker-compose -f docker-compose.full.yml up -d
```

注意：GPUがないマシンで実行する場合は、`docker-compose.full.yml`ファイル内のGPU関連の設定をコメントアウトしてください。

## トラブルシューティング

### ネットワーク接続

- セキュリティグループが必要なポートでインスタンス間のトラフィックを許可していることを確認
- 両インスタンスが互いにpingできることを確認
- Ollamaが`0.0.0.0`（すべてのインターフェース）にバインドしていることを確認

### よくある問題

1. **「Ollamaサービスに接続できない」**:
   - GPUインスタンスで正しいOllamaサービスが実行されていることを確認
   - セキュリティグループでポート11434がアクセス可能であることを確認
   - .envファイル内のOLLAMA_BASE_URLが正しいことを確認

2. **「MLflowの実行詳細を読み込めない」**:
   - MLflowが適切に構成されアクセス可能であることを確認
   - MLflowサーバーがアーティファクトディレクトリに書き込めることを確認

3. **「GPUエラー：nvidia-container-cli〜」**:
   - NVIDIA Container Toolkitが正しくインストールされていることを確認
   - CPUのみの環境では、GPU設定をコメントアウトして実行

## 高度な設定

### カスタムドメイン名の使用

IPアドレスの代わりにドメイン名を使用したい場合：

1. ドメイン名を登録し、EC2インスタンスを指すDNSレコードを設定
2. `.env`ファイルでIPアドレスの代わりにドメイン名を使用
3. オプション：適切なSSL終端のためにNGINXをリバースプロキシとして設定

### HTTPS設定

本番環境では、HTTPSの設定を推奨します：

1. CPUインスタンスにNGINXをインストール
2. フロントエンド、API、MLflow用のリバースプロキシとしてNGINXを設定
3. Let's Encryptを使用して無料のSSL証明書を取得

### 複数のGPUインスタンスのロードバランシング

複数のGPUインスタンスでスケーリングする場合：

1. 複数のGPUインスタンスにOllamaをデプロイ
2. リクエストを分散するためのロードバランサーを設定
3. APIがロードバランサーエンドポイントを使用するよう設定

## メンテナンスと更新

### プラットフォームの更新

プラットフォームを更新するには：

```bash
# 両インスタンスで実行
git pull
docker-compose -f <使用中の設定ファイル> down
docker-compose -f <使用中の設定ファイル> up -d --build
```

### データのバックアップ

バックアップが必要な重要なデータ：
- MLflowデータベースとアーティファクト：`./llm_eval_backend/mlflow/`
- 外部データ：`./external_data/`
- データセット：`./datasets/`
- Ollamaモデル：Dockerボリューム`ollama_data`

## モニタリングとロギング

- トラブルシューティングのためのDockerログの確認：
  ```bash
  docker-compose -f docker-compose.cpu.yml logs -f api
  docker-compose -f docker-compose.cpu.yml logs -f mlflow
  docker-compose -f docker-compose.gpu.yml logs -f ollama
  ```

- EC2インスタンスのCloudWatchモニタリングを設定（本番環境推奨）

## セキュリティに関する考慮事項

- APIキーなどの機密データは環境変数ではなくデータベースに保存
- 可能な場合はEC2インスタンスにAWS IAMロールを使用
- インスタンス間のプライベートネットワークにVPCの使用を検討
- Dockerイメージとシステムパッケージを定期的に更新

## コスト最適化

- 適切な場合はGPUにスポットインスタンスを使用
- 未使用時はGPUインスタンスを停止することを検討
- 負荷に基づいてCPUインスタンスのオートスケーリングを使用
- EBSボリュームを監視してストレージコストを最適化