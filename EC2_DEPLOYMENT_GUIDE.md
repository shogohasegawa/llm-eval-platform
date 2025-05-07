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

### EC2インスタンスの準備

1. **CPUインスタンス**（例：t3.xlarge）
   - 必要なスペック：少なくとも4 vCPU、16GB RAM
   - ストレージ：最低30GB（モデルの保存に応じて拡張）
   - AMI：Amazon Linux 2023またはUbuntu 22.04 LTS

2. **GPUインスタンス**（例：g4dn.xlarge）
   - 必要なスペック：NVIDIA GPUを搭載したインスタンス
   - ストレージ：最低50GB（Ollamaモデルの保存に応じて拡張）
   - AMI：Deep Learning AMI (Ubuntu 22.04)または独自にドライバをインストール

### セキュリティグループの設定

両方のインスタンスに以下のポートを開放します：

- **CPUインスタンス**
  - ポート4173（フロントエンド）- インターネットからアクセス可能に
  - ポート8001（API）- インターネットからアクセス可能に
  - ポート5000（MLflow）- インターネットからアクセス可能に（または必要に応じて制限）
  - ポート22（SSH）- 管理用

- **GPUインスタンス**
  - ポート11434（Ollama）- CPUインスタンスからアクセス可能に
  - ポート22（SSH）- 管理用

### 必要なソフトウェアのインストール

#### CPUインスタンスの設定

```bash
# Dockerのインストール（Ubuntuの場合）
sudo apt update
sudo apt install -y docker.io docker-compose

# Dockerサービスの開始と自動起動設定
sudo systemctl start docker
sudo systemctl enable docker

# 現在のユーザーをdockerグループに追加（再ログイン必要）
sudo usermod -aG docker $USER
```

#### GPUインスタンスの設定

```bash
# NVIDIA Driverとコンテナツールキットのインストール（Ubuntuの場合）
sudo apt update
sudo apt install -y docker.io docker-compose

# NVIDIAドライバとCUDAのインストール（Deep Learning AMIを使わない場合）
sudo apt install -y nvidia-driver-535 nvidia-cuda-toolkit

# NVIDIA Container Toolkitのインストール
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# 動作確認
sudo docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

## ステップ1：両インスタンスにリポジトリをクローン

```bash
git clone https://github.com/your-repo/llm-eval-platform.git
cd llm-eval-platform
```

## ステップ2：CPUインスタンスのセットアップ

1. メイン環境設定ファイルを作成：

```bash
# CPU側の環境設定ファイルの例をコピー
cp .env.cpu.example .env

# 実際のGPUインスタンスIPで.envファイルを編集
nano .env
```

**重要な設定項目：**
- `GPU_INSTANCE_IP`：GPUインスタンスの公開IPアドレスまたはプライベートIPを設定
- `API_BASE_URL`：自身のIPアドレスを指定（例: `http://your-cpu-instance-ip:8001`）

2. バックエンド用の環境設定が既に存在しており、必要に応じて調整します：

```bash
# 既存のサンプル設定をチェック
cat llm_eval_backend/.env.sample

# 必要に応じて編集
nano llm_eval_backend/.env
```

**主な設定項目：**
- `LLMEVAL_DATASET_DIR`：データセットディレクトリパス（通常は`/external_datasets/test/`）
- `LLMEVAL_TRAIN_DIR`：訓練データセットディレクトリパス（通常は`/external_datasets/n_shot/`）
- `LLMEVAL_MLFLOW_TRACKING_URI`：MLflowサーバーのURI（通常は`http://mlflow:5000`）

3. CPUインスタンスのコンポーネントを実行：

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
# GPU側の環境設定ファイルの例をコピー
cp .env.gpu.example .env

# 必要に応じて.envファイルを編集
nano .env
```

**重要な設定項目：**
- `GPU_COUNT`：使用するGPUの数（通常は1）
- `OLLAMA_HOST`：通常は`0.0.0.0`を指定（すべてのネットワークインターフェースでリッスン）

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
# メイン環境設定ファイルをコピー
cp .env.full.example .env

# バックエンド設定を必要に応じて調整
cat llm_eval_backend/.env.sample
nano llm_eval_backend/.env

# 必要に応じて.envファイルを編集
nano .env
```

2. すべてのサービスを起動：

```bash
docker-compose -f docker-compose.full.yml up -d
```

注意：GPUがないマシンで実行する場合は、`docker-compose.full.yml`ファイル内のGPU関連の設定（`runtime: nvidia`行と`NVIDIA_VISIBLE_DEVICES`環境変数）をコメントアウトしてください。

## トラブルシューティング

### ネットワーク接続

- セキュリティグループが必要なポートでインスタンス間のトラフィックを許可していることを確認
- 両インスタンスが互いにpingできることを確認
- Ollamaが`0.0.0.0`（すべてのインターフェース）にバインドしていることを確認
- VPC内でプライベートIPを使用している場合、正しいサブネット設定かを確認

### よくある問題

1. **「Ollamaサービスに接続できない」**:
   - GPUインスタンスで正しいOllamaサービスが実行されていることを確認
   - セキュリティグループでポート11434がアクセス可能であることを確認
   - .envファイル内のOLLAMA_BASE_URLが正しいことを確認
   ```bash
   # GPUインスタンスでのOllamaサービス状態確認
   docker ps | grep ollama
   docker logs ollama
   ```

2. **「MLflowの実行詳細を読み込めない」**:
   - MLflowが適切に構成されアクセス可能であることを確認
   - MLflowサーバーがアーティファクトディレクトリに書き込めることを確認
   ```bash
   # MLflowサービス状態確認
   docker logs llm-eval-platform_mlflow_1
   ```

3. **「GPUエラー：nvidia-container-cli〜」**:
   - NVIDIA Container Toolkitが正しくインストールされていることを確認
   - CPUのみの環境では、GPU設定をコメントアウトして実行
   ```bash
   # GPUドライバ確認
   nvidia-smi
   # NVIDIA Docker確認
   sudo docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
   ```

4. **「APIサーバーに接続できない」**:
   - APIサービスが正常に起動していることを確認
   - 環境変数の設定が正しいことを確認
   ```bash
   docker logs llm-eval-platform_api_1
   ```

5. **「データセットが見つからない」**:
   - バックエンド環境設定ファイル内の`LLMEVAL_DATASET_DIR`や`LLMEVAL_TRAIN_DIR`が正しく設定されているか確認
   - ボリュームマウントが正しく行われていることを確認
   ```bash
   # コンテナ内のマウント状況確認
   docker exec -it llm-eval-platform_api_1 ls -la /external_datasets
   ```

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
   ```bash
   sudo apt install -y nginx certbot python3-certbot-nginx
   ```
3. Let's Encryptを使用して無料のSSL証明書を取得
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

### 複数のGPUインスタンスのロードバランシング

複数のGPUインスタンスでスケーリングする場合：

1. 複数のGPUインスタンスにOllamaをデプロイ
2. HAProxyまたはNGINXでリクエストを分散するためのロードバランサーを設定
3. CPUインスタンスの`.env`ファイルで、`OLLAMA_BASE_URL`をロードバランサーのエンドポイントに設定

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

```bash
# Dockerボリュームのバックアップ例
docker run --rm -v ollama_data:/data -v $(pwd):/backup alpine tar -czvf /backup/ollama_data_backup.tar.gz /data
```

## モニタリングとロギング

- トラブルシューティングのためのDockerログの確認：
  ```bash
  docker-compose -f docker-compose.cpu.yml logs -f api
  docker-compose -f docker-compose.cpu.yml logs -f mlflow
  docker-compose -f docker-compose.gpu.yml logs -f ollama
  ```

- EC2インスタンスのCloudWatchモニタリングを設定（本番環境推奨）
  ```bash
  # CloudWatchエージェントのインストール例
  sudo amazon-linux-extras install -y collectd
  sudo amazon-linux-extras install -y amazon-cloudwatch-agent
  ```

## セキュリティに関する考慮事項

- APIキーなどの機密データは環境変数ではなくデータベースに保存
- 可能な場合はEC2インスタンスにAWS IAMロールを使用
- インスタンス間のプライベートネットワークにVPCの使用を検討
- Dockerイメージとシステムパッケージを定期的に更新
- ファイアウォールルールを最小権限の原則で設定

## コスト最適化

- 適切な場合はGPUにスポットインスタンスを使用
- 未使用時はGPUインスタンスを停止することを検討
- 負荷に基づいてCPUインスタンスのオートスケーリングを使用
- EBSボリュームを監視してストレージコストを最適化
- リザーブドインスタンスまたはSavings Plansを検討（長期運用の場合）