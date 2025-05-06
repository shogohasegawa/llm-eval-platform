import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Grid, 
  Paper, 
  CircularProgress,
  Alert,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  Tabs,
  Tab
} from '@mui/material';
import CodeIcon from '@mui/icons-material/Code';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { useMetrics, useMetricTypes, useDeleteMetric } from '../hooks/useMetrics';
import { useQueryClient } from '@tanstack/react-query';
import { Metric, MetricTypeInfo } from '../types/metrics';
import { useAppContext } from '../contexts/AppContext';
import MetricCard from '../components/metrics/MetricCard';
import { metricsApi } from '../api/metrics';

/**
 * 評価指標管理ページ
 */
const Metrics: React.FC = () => {
  // QueryClient
  const queryClient = useQueryClient();
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  
  // 評価指標削除の状態と関数
  const { mutate: deleteMetric, isLoading: isDeleting } = useDeleteMetric();
  
  // タブの状態
  const [tabIndex, setTabIndex] = useState(0); // 0: 組み込み評価指標, 1: カスタム評価指標
  
  // ダイアログの状態
  const [codeDialogOpen, setCodeDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [codeContent, setCodeContent] = useState<{filename: string, code: string, class_name: string} | null>(null);
  const [isLoadingCode, setIsLoadingCode] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  // 評価指標データの取得
  const { 
    data: metrics, 
    isLoading: isLoadingMetrics, 
    isError: isErrorMetrics, 
    error: metricsError 
  } = useMetrics();
  
  // 評価指標タイプの取得（組み込み指標）
  const { 
    data: metricTypes, 
    isLoading: isLoadingMetricTypes, 
    isError: isErrorMetricTypes, 
    error: metricTypesError 
  } = useMetricTypes();
  
  // メトリックデータのみを使用
  
  // ソースコードを取得する関数
  const fetchMetricCode = async (metricName: string) => {
    try {
      setIsLoadingCode(true);
      const codeData = await metricsApi.getMetricCode(metricName);
      setCodeContent(codeData);
      setCodeDialogOpen(true);
    } catch (error) {
      console.error('評価指標のコード取得エラー:', error);
      if (error instanceof Error) {
        setError(`評価指標のコード取得に失敗しました: ${error.message}`);
      }
    } finally {
      setIsLoadingCode(false);
    }
  };
  
  // エラーハンドリング
  if (metricTypesError) {
    setError(`評価指標タイプの取得に失敗しました: ${metricTypesError.message}`);
  }
  
  // アップロードダイアログを開く
  const handleOpenUploadDialog = () => {
    setSelectedFile(null);
    setUploadError(null);
    setUploadDialogOpen(true);
  };
  
  // タブ変更ハンドラ
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabIndex(newValue);
  };
  
  // ファイル選択ハンドラ
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      setUploadError(null);
    }
  };
  
  // ファイルアップロードハンドラ
  const handleUploadFile = async () => {
    if (!selectedFile) {
      setUploadError("ファイルを選択してください。");
      return;
    }
    
    if (!selectedFile.name.endsWith('.py')) {
      setUploadError("Pythonファイル(.py)を選択してください。");
      return;
    }
    
    try {
      setIsUploading(true);
      setUploadError(null);
      
      const response = await metricsApi.uploadMetricFile(selectedFile);
      console.log('アップロード成功:', response);
      
      // アップロード成功時の処理
      setUploadDialogOpen(false);
      setSelectedFile(null);
      
      // 評価指標一覧を再取得
      await Promise.all([
        queryClient.invalidateQueries(['metrics']),
        queryClient.invalidateQueries(['metricTypes'])
      ]);
      
      // 成功メッセージを表示
      setError(`評価指標「${response.metrics}」のアップロードに成功しました。`, "success");
      
      // カスタム評価指標タブに切り替え
      setTabIndex(1);
      
    } catch (error) {
      console.error('ファイルアップロードエラー:', error);
      if (error instanceof Error) {
        setUploadError(`アップロードに失敗しました: ${error.message}`);
      } else {
        setUploadError("アップロードに失敗しました。");
      }
    } finally {
      setIsUploading(false);
    }
  };
  
  // アップロードダイアログを閉じる
  const handleCloseUploadDialog = () => {
    setUploadDialogOpen(false);
    setSelectedFile(null);
    setUploadError(null);
  };
  
  // ローディング中
  const isLoading = isLoadingMetricTypes;
  
  // 評価指標削除の処理
  const handleDeleteMetric = (metricName: string) => {
    deleteMetric(metricName, {
      onSuccess: (data) => {
        setError(`評価指標「${data.name}」を削除しました。`, "success");
        
        // 評価指標一覧を再取得
        queryClient.invalidateQueries({ queryKey: ['metrics'] });
        queryClient.invalidateQueries({ queryKey: ['metricTypes'] });
      },
      onError: (error: Error) => {
        setError(`評価指標の削除に失敗しました: ${error.message}`);
      }
    });
  };

  // 組み込み評価指標とカスタム評価指標を分離
  const builtinMetrics = metricTypes?.filter(metric => !metric.is_custom) || [];
  const customMetrics = metricTypes?.filter(metric => metric.is_custom) || [];

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          評価指標管理
        </Typography>
        
        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            startIcon={<UploadFileIcon />}
            onClick={handleOpenUploadDialog}
            color="primary"
          >
            Pythonファイルをアップロード
          </Button>
        </Stack>
      </Box>
      
      <Typography variant="body1" sx={{ mb: 2 }}>
        カスタム評価指標を追加するには、BaseMetricクラスを継承したPythonファイルをアップロードしてください。
      </Typography>
      
      <Divider sx={{ mb: 3 }} />
      
      {/* タブ切り替え */}
      <Tabs 
        value={tabIndex}
        onChange={handleTabChange}
        sx={{ mb: 3 }}
        indicatorColor="primary"
        textColor="primary"
      >
        <Tab label="組み込み評価指標" />
        <Tab label="カスタム評価指標" />
      </Tabs>
      
      {/* 評価指標を表示 */}
      {isLoadingMetricTypes ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : isErrorMetricTypes ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          評価指標の取得中にエラーが発生しました。
        </Alert>
      ) : (
        <>
          {/* 組み込み評価指標のタブ */}
          {tabIndex === 0 && (
            <>
              {builtinMetrics.length > 0 ? (
                <Grid container spacing={2}>
                  {builtinMetrics.map((metric) => (
                    <Grid item xs={12} sm={6} md={4} key={metric.name}>
                      <MetricCard
                        metric={{
                          id: metric.name,
                          name: metric.name,
                          type: 'builtin',
                          description: metric.description || '',
                          isHigherBetter: metric.is_higher_better,
                          parameters: metric.parameters || {},
                          createdAt: new Date(),
                          updatedAt: new Date()
                        }}
                        onViewCode={(metricName) => fetchMetricCode(metricName)}
                        onEdit={null} // 編集機能を無効化
                        onDelete={null} // 組み込み評価指標は削除できない
                      />
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    組み込み評価指標が見つかりません。
                  </Typography>
                </Paper>
              )}
            </>
          )}
          
          {/* カスタム評価指標のタブ */}
          {tabIndex === 1 && (
            <>
              {customMetrics.length > 0 ? (
                <Grid container spacing={2}>
                  {customMetrics.map((metric) => (
                    <Grid item xs={12} sm={6} md={4} key={metric.name}>
                      <MetricCard
                        metric={{
                          id: metric.name,
                          name: metric.name,
                          type: 'custom',
                          description: metric.description || '',
                          isHigherBetter: metric.is_higher_better,
                          is_custom: true, // カスタム評価指標フラグを追加
                          parameters: metric.parameters || {},
                          createdAt: new Date(),
                          updatedAt: new Date()
                        }}
                        onViewCode={(metricName) => fetchMetricCode(metricName)}
                        onEdit={null} // 編集機能を無効化
                        onDelete={handleDeleteMetric} // 削除機能を有効化
                      />
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    カスタム評価指標が見つかりません。「Pythonファイルをアップロード」ボタンを使用して追加してください。
                  </Typography>
                </Paper>
              )}
            </>
          )}
        </>
      )}
      
      {/* 評価指標コード表示ダイアログ */}
      <Dialog 
        open={codeDialogOpen} 
        onClose={() => setCodeDialogOpen(false)} 
        fullWidth 
        maxWidth="md"
        aria-labelledby="metric-code-dialog"
      >
        <DialogTitle id="metric-code-dialog">
          {codeContent ? `${codeContent.class_name} (${codeContent.filename})` : '評価指標コード'}
        </DialogTitle>
        <DialogContent dividers>
          {isLoadingCode ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : codeContent ? (
            <Box 
              component="pre" 
              sx={{ 
                fontFamily: 'monospace', 
                fontSize: '0.9rem',
                backgroundColor: '#f5f5f5',
                p: 2,
                borderRadius: 1,
                border: '1px solid #e0e0e0',
                maxHeight: '70vh',
                overflow: 'auto'
              }}
            >
              {codeContent.code}
            </Box>
          ) : (
            <Typography>コードが見つかりません。</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCodeDialogOpen(false)}>閉じる</Button>
        </DialogActions>
      </Dialog>
      
      {/* 評価指標ファイルアップロードダイアログ */}
      <Dialog 
        open={uploadDialogOpen} 
        onClose={handleCloseUploadDialog} 
        fullWidth 
        maxWidth="sm"
        aria-labelledby="metric-upload-dialog"
      >
        <DialogTitle id="metric-upload-dialog">
          評価指標のPythonファイルをアップロード
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ p: 2 }}>
            <Typography variant="body1" gutterBottom>
              BaseMetricを継承した評価指標クラスを含むPythonファイル(.py)をアップロードしてください。
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              注意: アップロードされたファイルはサーバー上で実行されます。セキュリティ上の理由から、
              安全なコードのみをアップロードしてください。
            </Typography>
            
            <Box sx={{ mt: 2, mb: 3 }}>
              <input
                accept=".py"
                id="metric-file-upload"
                type="file"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <label htmlFor="metric-file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<UploadFileIcon />}
                  disabled={isUploading}
                >
                  ファイルを選択
                </Button>
              </label>
              {selectedFile && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  選択されたファイル: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                </Typography>
              )}
            </Box>
            
            {uploadError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {uploadError}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseUploadDialog} disabled={isUploading}>
            キャンセル
          </Button>
          <Button 
            onClick={handleUploadFile} 
            variant="contained" 
            color="primary"
            disabled={!selectedFile || isUploading}
            startIcon={isUploading ? <CircularProgress size={20} /> : null}
          >
            {isUploading ? 'アップロード中...' : 'アップロード'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Metrics;
