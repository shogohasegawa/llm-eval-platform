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

# Vite の開発サーバーを使用（本番でも開発モード）
CMD ["npm", "run", "start"]
