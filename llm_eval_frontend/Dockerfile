# Node.js 18 ベース
FROM node:18

# 作業ディレクトリ
WORKDIR /app

# curl をインストール（ヘルスチェック用）
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# パッケージをインストール
COPY package.json package-lock.json ./
RUN npm install

# ソースコードをコピー
COPY . .

# API_HOSTを環境変数として設定（デフォルト値を設定し、実行時に上書き可能にする）
ENV API_HOST=${VITE_API_HOST:-llm-api-backend}

# Vite の開発サーバーを使用（ネットワークアクセス可能に設定）
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "3000"]
