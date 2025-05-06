import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import { fileURLToPath } from 'url';

// ES modules compatibility: get __dirname equivalent
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 3000;

// API Proxy設定 (ターゲットを固定で設定)
const apiProxy = createProxyMiddleware('/api', {
  target: 'http://api:8000',
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
  console.log(`API proxy target: http://api:8000`);
  console.log(`=====================================`);
});