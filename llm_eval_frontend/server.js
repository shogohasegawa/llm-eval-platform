import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import { fileURLToPath } from 'url';

// ES modules compatibility: get __dirname equivalent
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 3000;

// API Proxy設定 (環境変数から設定を取得、またはデフォルト値を使用)
const API_HOST = process.env.VITE_API_HOST || 'llm-api-backend';
const API_PORT = process.env.VITE_API_PORT || '8000';
const API_URL = process.env.VITE_API_BASE_URL || `http://${API_HOST}:${API_PORT}`;

const apiProxy = createProxyMiddleware('/api', {
  target: API_URL,
  changeOrigin: true,
  secure: false,
  logLevel: 'debug',
  onProxyReq: (proxyReq, req) => {
    console.log(`Proxying request: ${req.method} ${req.url} -> ${proxyReq.path}`);
  },
  onProxyRes: (proxyRes, req) => {
    console.log(`Proxy response: ${req.method} ${req.url} -> ${proxyRes.statusCode}`);
  },
  onError: (err, req, res) => {
    console.error('Proxy error:', err);
    res.status(500).json({
      error: 'Proxy Error',
      message: 'Could not connect to the backend API',
      details: err.message
    });
  }
});

// 静的ファイルのホスティング（Viteビルド結果）
app.use(express.static(path.join(__dirname, 'dist')));

// APIパスをプロキシ
app.use('/api', apiProxy);

// すべてのリクエストをindex.htmlにリダイレクト（SPAルーティング用）
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

// サーバー起動
app.listen(port, () => {
  console.log(`==== LLM Evaluation Platform Frontend ====`);
  console.log(`Server running on port ${port}`);
  console.log(`API proxy target: ${API_URL}`);
  console.log(`=====================================`);
});