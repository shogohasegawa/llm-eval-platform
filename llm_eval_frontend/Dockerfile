# Node.js 18 ベース
FROM node:18

# 作業ディレクトリ
WORKDIR /app

# パッケージをインストール
COPY package.json package-lock.json ./
RUN npm install

# ソースコードをコピー
COPY . .

# フロントエンドのビルド（vite preview 用）
RUN npm run build

# API と フロントを同時に起動
CMD ["npm", "run", "start"]
