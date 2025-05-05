import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider } from './contexts/AppContext';
import { ThemeContextProvider } from './contexts/ThemeContext';
import Providers from './pages/Providers';
import ProviderDetail from './pages/ProviderDetail';
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
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5分
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
