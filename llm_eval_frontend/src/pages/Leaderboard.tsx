import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Grid, 
  Paper, 
  CircularProgress,
  Alert,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Tooltip,
  IconButton,
  SelectChangeEvent
} from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import InfoIcon from '@mui/icons-material/Info';
import { useLeaderboard, useExportLeaderboard, useMetrics } from '../hooks/useMetrics';
import { useDatasets } from '../hooks/useDatasets';
import { useProviders } from '../hooks/useProviders';
import { LeaderboardFilterOptions } from '../types/metrics';
import { useAppContext } from '../contexts/AppContext';

/**
 * リーダーボードページ
 */
const Leaderboard: React.FC = () => {
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  
  // フィルター状態
  const [filters, setFilters] = useState<LeaderboardFilterOptions>({
    limit: 10
  });
  
  // データの取得
  const { 
    data: leaderboard, 
    isLoading: isLoadingLeaderboard, 
    isError: isErrorLeaderboard, 
    error: leaderboardError 
  } = useLeaderboard(filters);
  
  const { data: metrics } = useMetrics();
  const { data: datasets } = useDatasets();
  const { data: providers } = useProviders();
  
  // エクスポート機能
  const exportLeaderboard = useExportLeaderboard();
  
  // エラーハンドリング
  if (leaderboardError) {
    setError(`リーダーボードの取得に失敗しました: ${leaderboardError.message}`);
  }
  
  // フィルターの変更処理
  const handleFilterChange = (e: SelectChangeEvent<string | number>) => {
    const { name, value } = e.target;
    if (name) {
      setFilters(prev => ({
        ...prev,
        [name]: value === 'all' ? undefined : value
      }));
    }
  };
  
  // リーダーボードのエクスポート
  const handleExportLeaderboard = async () => {
    try {
      const blob = await exportLeaderboard.mutateAsync(filters);
      
      // ダウンロードリンクを作成
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `leaderboard_export_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      
      // クリーンアップ
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      if (err instanceof Error) {
        setError(`リーダーボードのエクスポートに失敗しました: ${err.message}`);
      }
    }
  };
  
  // 選択された評価指標
  const selectedMetric = metrics?.find(m => m.id === filters.metricId);
  
  // ローディング中
  const isLoading = isLoadingLeaderboard;
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          リーダーボード
        </Typography>
        <Button
          variant="outlined"
          startIcon={<FileDownloadIcon />}
          onClick={handleExportLeaderboard}
          disabled={exportLeaderboard.isPending || !leaderboard || leaderboard.length === 0}
        >
          CSVエクスポート
        </Button>
      </Box>
      
      <Divider sx={{ mb: 3 }} />
      
      {/* フィルター */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>データセット</InputLabel>
              <Select
                name="datasetId"
                value={filters.datasetId || 'all'}
                onChange={handleFilterChange}
                label="データセット"
              >
                <MenuItem value="all">すべて</MenuItem>
                {datasets?.map((dataset) => (
                  <MenuItem key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>プロバイダ</InputLabel>
              <Select
                name="providerId"
                value={filters.providerId || 'all'}
                onChange={handleFilterChange}
                label="プロバイダ"
              >
                <MenuItem value="all">すべて</MenuItem>
                {providers?.map((provider) => (
                  <MenuItem key={provider.id} value={provider.id}>
                    {provider.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>評価指標</InputLabel>
              <Select
                name="metricId"
                value={filters.metricId || 'all'}
                onChange={handleFilterChange}
                label="評価指標"
              >
                <MenuItem value="all">すべて</MenuItem>
                {metrics?.map((metric) => (
                  <MenuItem key={metric.id} value={metric.id}>
                    {metric.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>表示件数</InputLabel>
              <Select
                name="limit"
                value={filters.limit || 10}
                onChange={handleFilterChange}
                label="表示件数"
              >
                <MenuItem value={5}>5件</MenuItem>
                <MenuItem value={10}>10件</MenuItem>
                <MenuItem value={20}>20件</MenuItem>
                <MenuItem value={50}>50件</MenuItem>
                <MenuItem value={100}>100件</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>
      
      {isLoading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : isErrorLeaderboard ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          リーダーボードの取得中にエラーが発生しました。
        </Alert>
      ) : leaderboard && leaderboard.length > 0 ? (
        <TableContainer component={Paper}>
          <Table sx={{ minWidth: 650 }} aria-label="リーダーボードテーブル">
            <TableHead>
              <TableRow>
                <TableCell>順位</TableCell>
                <TableCell>モデル</TableCell>
                <TableCell>プロバイダ</TableCell>
                <TableCell>データセット</TableCell>
                {selectedMetric ? (
                  <TableCell>
                    <Box display="flex" alignItems="center">
                      {selectedMetric.name}
                      <Tooltip title={`${selectedMetric.description || selectedMetric.name}（${selectedMetric.isHigherBetter ? '高いほど良い' : '低いほど良い'}）`}>
                        <IconButton size="small">
                          <InfoIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                ) : (
                  <TableCell>評価指標</TableCell>
                )}
                <TableCell>実行日時</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {leaderboard.map((entry) => (
                <TableRow key={entry.inferenceId}>
                  <TableCell>
                    <Chip 
                      label={`#${entry.rank}`} 
                      color={entry.rank <= 3 ? "primary" : "default"} 
                      variant={entry.rank <= 3 ? "filled" : "outlined"} 
                    />
                  </TableCell>
                  <TableCell>{entry.modelName}</TableCell>
                  <TableCell>{entry.providerName}</TableCell>
                  <TableCell>{entry.datasetName}</TableCell>
                  {selectedMetric ? (
                    <TableCell>
                      <Typography variant="body1" fontWeight="bold">
                        {entry.metrics[selectedMetric.id]?.toFixed(4) || '-'}
                      </Typography>
                    </TableCell>
                  ) : (
                    <TableCell>
                      {Object.entries(entry.metrics).map(([key, value]) => {
                        const metric = metrics?.find(m => m.id === key);
                        return (
                          <Box key={key} mb={0.5}>
                            <Typography variant="body2">
                              {metric?.name || key}: {value.toFixed(4)}
                            </Typography>
                          </Box>
                        );
                      })}
                    </TableCell>
                  )}
                  <TableCell>
                    {new Date(entry.createdAt).toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            リーダーボードデータがありません。推論を実行し、評価指標を適用してリーダーボードを生成してください。
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default Leaderboard;
