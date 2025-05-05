import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Grid, 
  Paper, 
  CircularProgress,
  Alert,
  Divider
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { useMetrics, useCreateMetric, useUpdateMetric, useDeleteMetric } from '../hooks/useMetrics';
import { Metric, MetricFormData } from '../types/metrics';
import { useAppContext } from '../contexts/AppContext';
import MetricCard from '../components/metrics/MetricCard';
import MetricFormDialog from '../components/metrics/MetricFormDialog';

/**
 * 評価指標管理ページ
 */
const Metrics: React.FC = () => {
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  
  // ダイアログの状態
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState<Metric | undefined>(undefined);
  
  // 評価指標データの取得
  const { 
    data: metrics, 
    isLoading: isLoadingMetrics, 
    isError: isErrorMetrics, 
    error: metricsError 
  } = useMetrics();
  
  // ミューテーションフック
  const createMetric = useCreateMetric();
  const updateMetric = useUpdateMetric(selectedMetric?.id || '');
  const deleteMetric = useDeleteMetric();
  
  // エラーハンドリング
  if (metricsError) {
    setError(`評価指標の取得に失敗しました: ${metricsError.message}`);
  }
  
  // 評価指標の作成ダイアログを開く
  const handleOpenCreateDialog = () => {
    setSelectedMetric(undefined);
    setFormDialogOpen(true);
  };
  
  // 評価指標の編集ダイアログを開く
  const handleOpenEditDialog = (metric: Metric) => {
    setSelectedMetric(metric);
    setFormDialogOpen(true);
  };
  
  // ダイアログを閉じる
  const handleCloseDialog = () => {
    setFormDialogOpen(false);
    setSelectedMetric(undefined);
  };
  
  // 評価指標の作成または更新を実行
  const handleSubmitMetric = async (data: MetricFormData) => {
    try {
      if (selectedMetric) {
        // 更新
        await updateMetric.mutateAsync(data);
      } else {
        // 作成
        await createMetric.mutateAsync(data);
      }
      handleCloseDialog();
    } catch (err) {
      if (err instanceof Error) {
        setError(`評価指標の${selectedMetric ? '更新' : '作成'}に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 評価指標の削除を実行
  const handleDeleteMetric = async (id: string) => {
    try {
      await deleteMetric.mutateAsync(id);
    } catch (err) {
      if (err instanceof Error) {
        setError(`評価指標の削除に失敗しました: ${err.message}`);
      }
    }
  };
  
  // ローディング中
  const isLoading = isLoadingMetrics;
  
  // 送信中
  const isSubmitting = createMetric.isPending || updateMetric.isPending;
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          評価指標管理
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreateDialog}
        >
          評価指標を追加
        </Button>
      </Box>
      
      <Divider sx={{ mb: 3 }} />
      
      {isLoading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : isErrorMetrics ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          評価指標の取得中にエラーが発生しました。
        </Alert>
      ) : metrics && metrics.length > 0 ? (
        <Grid container spacing={2}>
          {metrics.map((metric) => (
            <Grid item xs={12} sm={6} md={4} key={metric.id}>
              <MetricCard
                metric={metric}
                onEdit={handleOpenEditDialog}
                onDelete={handleDeleteMetric}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            カスタム評価指標が登録されていません。「評価指標を追加」ボタンをクリックして新しい評価指標を作成してください。
            評価指標を追加すると、この画面に表示されます。
          </Typography>
        </Paper>
      )}
      
      {/* 評価指標作成・編集ダイアログ */}
      {formDialogOpen && (
        <MetricFormDialog
          open={formDialogOpen}
          onClose={handleCloseDialog}
          onSubmit={handleSubmitMetric}
          initialData={selectedMetric}
          isSubmitting={isSubmitting}
        />
      )}
    </Box>
  );
};

export default Metrics;
