import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider } from './contexts/AppContext';
import { ThemeContextProvider } from './contexts/ThemeContext';

// 環境変数のロギング（デバッグ用）
if (import.meta.env.VITE_DEBUG_MODE === 'true') {
  console.log('App Config:', {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
    appName: import.meta.env.VITE_APP_NAME,
    appVersion: import.meta.env.VITE_APP_VERSION,
    logLevel: import.meta.env.VITE_LOG_LEVEL,
  });
}
import Providers from './pages/Providers';
import ProviderDetail from './pages/ProviderDetail';
import Models from './pages/Models';
import ModelDetail from './pages/ModelDetail';
import Datasets from './pages/Datasets';
import DatasetDetail from './pages/DatasetDetail';
import Inferences from './pages/Inferences';
import InferenceDetail from './pages/InferenceDetail';
import Metrics from './pages/Metrics';
import Leaderboard from './pages/Leaderboard';
import Layout from './components/common/Layout';

// React Queryクライアントの作成
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true, // ウィンドウフォーカス時に更新
      refetchOnMount: true,      // コンポーネントマウント時に更新
      refetchOnReconnect: true,  // ネットワーク再接続時に更新
      retry: 3,                  // エラー時のリトライ回数
      staleTime: 10000,          // 10秒でデータを古いとみなす
      cacheTime: 5 * 60 * 1000,  // 5分間キャッシュを保持
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppProvider>
        <ThemeContextProvider>
          <Router>
            <Routes>
              <Route path="/" element={<Layout />}>
                <Route index element={<Navigate to="/providers" replace />} />
                <Route path="providers" element={<Providers />} />
                <Route path="providers/:id" element={<ProviderDetail />} />
                <Route path="models" element={<Models />} />
                <Route path="models/:id" element={<ModelDetail />} />
                <Route path="datasets" element={<Datasets />} />
                <Route path="datasets/:id" element={<DatasetDetail />} />
                <Route path="inferences" element={<Inferences />} />
                <Route path="inferences/:id" element={<InferenceDetail />} />
                <Route path="metrics" element={<Metrics />} />
                <Route path="leaderboard" element={<Leaderboard />} />
                <Route path="*" element={<Navigate to="/providers" replace />} />
              </Route>
            </Routes>
          </Router>
        </ThemeContextProvider>
      </AppProvider>
    </QueryClientProvider>
  );
}

export default App;
