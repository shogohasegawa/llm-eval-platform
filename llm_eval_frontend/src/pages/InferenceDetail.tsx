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
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  Card,
  CardContent
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import { useParams, useNavigate } from 'react-router-dom';
import { useInference, useInferenceResults, useRunInference, useStopInference, useExportInferenceResults } from '../hooks/useInferences';
import { useDatasetByName } from '../hooks/useDatasets';
import { useProvider } from '../hooks/useProviders';
import { InferenceResult } from '../types/inference';
import { useAppContext } from '../contexts/AppContext';

/**
 * 推論詳細ページ
 */
const InferenceDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const inferenceId = id || '';

  // コンテキストから状態を取得
  const { setError } = useAppContext();

  // タブの状態
  const [tabValue, setTabValue] = useState(0);

  // ポーリング間隔（ミリ秒）
  const pollingInterval = 5000;

  // 推論データの取得
  const {
    data: inference,
    isLoading: isLoadingInference,
    isError: isErrorInference,
    error: inferenceError,
    refetch: refetchInference
  } = useInference(inferenceId);

  // 推論結果の取得
  const {
    data: results,
    isLoading: isLoadingResults,
    isError: isErrorResults,
    error: resultsError,
    refetch: refetchResults
  } = useInferenceResults(inferenceId);

  // 関連データの取得
  const { data: dataset } = useDatasetByName(inference?.datasetId || '');
  const { data: provider } = useProvider(inference?.providerId || '');

  // ミューテーションフック
  const runInference = useRunInference(inferenceId);
  const stopInference = useStopInference(inferenceId);
  const exportResults = useExportInferenceResults(inferenceId);

  // 実行中の推論のポーリング
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (inference?.status === 'running') {
      intervalId = setInterval(() => {
        refetchInference();
        refetchResults();
      }, pollingInterval);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [inference?.status, refetchInference, refetchResults]);

  // エラーハンドリング
  if (inferenceError) {
    setError(`推論の取得に失敗しました: ${inferenceError.message}`);
  }

  if (resultsError) {
    setError(`推論結果の取得に失敗しました: ${resultsError.message}`);
  }

  // タブの変更ハンドラ
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // 推論の実行を開始
  const handleRunInference = async () => {
    try {
      await runInference.mutateAsync();
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の実行に失敗しました: ${err.message}`);
      }
    }
  };

  // 推論の実行を停止
  const handleStopInference = async () => {
    try {
      await stopInference.mutateAsync();
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の停止に失敗しました: ${err.message}`);
      }
    }
  };

  // 推論結果のエクスポート
  const handleExportResults = async () => {
    try {
      const blob = await exportResults.mutateAsync();

      // ダウンロードリンクを作成
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `inference_results_${inferenceId}.csv`;
      document.body.appendChild(a);
      a.click();

      // クリーンアップ
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論結果のエクスポートに失敗しました: ${err.message}`);
      }
    }
  };

  // 推論一覧に戻る
  const handleBackToInferences = () => {
    navigate('/inferences');
  };

  // 推論ステータスに応じた色を設定
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return '#757575';
      case 'running':
        return '#2196F3';
      case 'completed':
        return '#4CAF50';
      case 'failed':
        return '#F44336';
      default:
        return '#757575';
    }
  };

  // 推論ステータスに応じた表示テキストを設定
  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return '待機中';
      case 'running':
        return '実行中';
      case 'completed':
        return '完了';
      case 'failed':
        return '失敗';
      default:
        return '不明';
    }
  };

  // 実行ボタンの表示条件
  const showRunButton = inference?.status === 'pending' || inference?.status === 'failed';

  // 停止ボタンの表示条件
  const showStopButton = inference?.status === 'running';

  // ローディング中
  if (isLoadingInference) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  // エラー発生時
  if (isErrorInference || !inference) {
    return (
      <Box p={3}>
        <Alert severity="error" sx={{ mb: 3 }}>
          推論の取得中にエラーが発生しました。
        </Alert>
        <Button variant="outlined" onClick={handleBackToInferences}>
          推論一覧に戻る
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Button variant="outlined" onClick={handleBackToInferences} sx={{ mb: 1 }}>
            推論一覧に戻る
          </Button>
          <Typography variant="h4" component="h1">
            {inference.name}
          </Typography>
          <Box display="flex" alignItems="center" mt={1}>
            <Chip
              label={getStatusText(inference.status)}
              sx={{
                backgroundColor: getStatusColor(inference.status),
                color: 'white',
                mr: 2
              }}
            />
            {inference.status === 'running' && (
              <Typography variant="body1">
                進捗: {inference.progress}%
              </Typography>
            )}
          </Box>
        </Box>
        <Box>
          {inference.status === 'completed' && (
            <Button
              variant="outlined"
              startIcon={<FileDownloadIcon />}
              onClick={handleExportResults}
              sx={{ mr: 1 }}
              disabled={exportResults.isPending}
            >
              結果をエクスポート
            </Button>
          )}
          {showRunButton && (
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon />}
              onClick={handleRunInference}
              color="primary"
              disabled={runInference.isPending}
            >
              実行
            </Button>
          )}
          {showStopButton && (
            <Button
              variant="contained"
              startIcon={<StopIcon />}
              onClick={handleStopInference}
              color="warning"
              disabled={stopInference.isPending}
            >
              停止
            </Button>
          )}
        </Box>
      </Box>

      {inference.status === 'running' && (
        <Box sx={{ width: '100%', mb: 3 }}>
          <LinearProgress variant="determinate" value={inference.progress} />
        </Box>
      )}

      <Divider sx={{ mb: 3 }} />

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="inference tabs">
          <Tab label="結果" id="tab-0" />
          <Tab label="詳細" id="tab-1" />
          <Tab label="メトリクス" id="tab-2" />
        </Tabs>
      </Box>

      {/* 結果タブ */}
      {tabValue === 0 && (
        <>
          {isLoadingResults ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : isErrorResults ? (
            <Alert severity="error" sx={{ mb: 3 }}>
              推論結果の取得中にエラーが発生しました。
            </Alert>
          ) : results && results.length > 0 ? (
            <TableContainer component={Paper}>
              <Table sx={{ minWidth: 650 }} aria-label="推論結果テーブル">
                <TableHead>
                  <TableRow>
                    <TableCell>入力</TableCell>
                    <TableCell>期待される出力</TableCell>
                    <TableCell>実際の出力</TableCell>
                    <TableCell>レイテンシ</TableCell>
                    <TableCell>トークン数</TableCell>
                    <TableCell>エラー</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {results.map((result) => (
                    <TableRow key={result.id}>
                      <TableCell sx={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {result.input}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {result.expectedOutput || '-'}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {result.actualOutput || '-'}
                      </TableCell>
                      <TableCell>
                        {result.latency ? `${result.latency}ms` : '-'}
                      </TableCell>
                      <TableCell>
                        {result.tokenCount || '-'}
                      </TableCell>
                      <TableCell>
                        {result.error || '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                {inference.status === 'pending'
                  ? '推論はまだ実行されていません。「実行」ボタンをクリックして推論を開始してください。'
                  : inference.status === 'running'
                    ? '推論を実行中です。結果が生成されるまでお待ちください。'
                    : '推論結果がありません。'}
              </Typography>
            </Paper>
          )}
        </>
      )}

      {/* 詳細タブ */}
      {tabValue === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  基本情報
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={4}>
                    <Typography variant="subtitle2">名前</Typography>
                  </Grid>
                  <Grid item xs={8}>
                    <Typography variant="body1">{inference.name}</Typography>
                  </Grid>

                  <Grid item xs={4}>
                    <Typography variant="subtitle2">ステータス</Typography>
                  </Grid>
                  <Grid item xs={8}>
                    <Chip
                      label={getStatusText(inference.status)}
                      size="small"
                      sx={{
                        backgroundColor: getStatusColor(inference.status),
                        color: 'white'
                      }}
                    />
                  </Grid>

                  <Grid item xs={4}>
                    <Typography variant="subtitle2">データセット</Typography>
                  </Grid>
                  <Grid item xs={8}>
                    <Typography variant="body1">{dataset?.name || inference.datasetId}</Typography>
                  </Grid>

                  <Grid item xs={4}>
                    <Typography variant="subtitle2">プロバイダ</Typography>
                  </Grid>
                  <Grid item xs={8}>
                    <Typography variant="body1">{provider?.name || inference.providerId}</Typography>
                  </Grid>

                  <Grid item xs={4}>
                    <Typography variant="subtitle2">モデル</Typography>
                  </Grid>
                  <Grid item xs={8}>
                    <Typography variant="body1">{inference.modelId}</Typography>
                  </Grid>

                  <Grid item xs={4}>
                    <Typography variant="subtitle2">作成日</Typography>
                  </Grid>
                  <Grid item xs={8}>
                    <Typography variant="body1">
                      {new Date(inference.createdAt).toLocaleString()}
                    </Typography>
                  </Grid>

                  {inference.completedAt && (
                    <>
                      <Grid item xs={4}>
                        <Typography variant="subtitle2">完了日</Typography>
                      </Grid>
                      <Grid item xs={8}>
                        <Typography variant="body1">
                          {new Date(inference.completedAt).toLocaleString()}
                        </Typography>
                      </Grid>
                    </>
                  )}
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  説明
                </Typography>
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                  {inference.description || '説明はありません。'}
                </Typography>

                {inference.error && (
                  <Box mt={2}>
                    <Typography variant="h6" gutterBottom color="error">
                      エラー
                    </Typography>
                    <Typography variant="body1" color="error">
                      {inference.error}
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* メトリクスタブ */}
      {tabValue === 2 && (
        <>
          {inference.metrics && Object.keys(inference.metrics).length > 0 ? (
            <Grid container spacing={3}>
              {Object.entries(inference.metrics).map(([key, value]) => (
                <Grid item xs={12} sm={6} md={4} key={key}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        {key}
                      </Typography>
                      <Typography variant="h4" align="center">
                        {typeof value === 'number' ? value.toFixed(4) : value}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                {inference.status === 'completed'
                  ? 'メトリクスが計算されていません。'
                  : '推論が完了するとメトリクスが表示されます。'}
              </Typography>
            </Paper>
          )}
        </>
      )}
    </Box>
  );
};

export default InferenceDetail;
