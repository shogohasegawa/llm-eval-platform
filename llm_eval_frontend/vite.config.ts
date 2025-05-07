import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // Listen on all addresses
    proxy: {
      '/api': {
        // APIサーバーのアドレスを設定
        // Docker Compose内では 'api' コンテナへの接続が可能
        // 複数環境対応：環境変数 -> Docker コンテナ名 -> ローカルホスト の順で優先
        target: process.env.VITE_API_BASE_URL || 'http://api:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
            // エラー発生時にフォールバックを試行
            console.log('Trying fallback connection to localhost...');
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Sending Request:', req.method, req.url, '→', proxyReq.path);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response:', req.method, req.url, '←', proxyRes.statusCode);
          });
        },
      },
    },
    watch: {
      ignored: ['**/node_modules/**', '**/dist/**', '**/.git/**'],
      usePolling: true,
      interval: 100,
    },
  },
});