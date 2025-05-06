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
import { useInference, useInferenceResults, useRunInference, useStopInference, useExportInferenceResults, useInferenceDetail } from '../hooks/useInferences';
import { useDatasetByName } from '../hooks/useDatasets';
import { useProvider, useModel } from '../hooks/useProviders';
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
  
  // 推論詳細情報の取得
  const {
    data: inferenceDetail,
    isLoading: isLoadingDetail,
    isError: isErrorDetail,
    error: detailError,
    refetch: refetchDetail
  } = useInferenceDetail(inferenceId);

  // 関連データの取得
  const { data: dataset } = useDatasetByName(inference?.datasetId || '');
  const { data: provider } = useProvider(inference?.providerId || '');
  const { data: model } = useModel(inference?.modelId || '');

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
        refetchDetail();
      }, pollingInterval);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [inference?.status, refetchInference, refetchResults, refetchDetail]);

  // エラーハンドリング
  if (inferenceError) {
    setError(`推論の取得に失敗しました: ${inferenceError.message}`);
  }

  if (resultsError) {
    setError(`推論結果の取得に失敗しました: ${resultsError.message}`);
  }
  
  if (detailError) {
    setError(`推論詳細情報の取得に失敗しました: ${detailError.message}`);
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
              <Box display="flex" alignItems="center">
                <CircularProgress size={20} sx={{ mr: 1 }} />
                <Typography variant="body1">
                  処理中...
                </Typography>
              </Box>
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
          <LinearProgress variant="indeterminate" />
        </Box>
      )}

      <Divider sx={{ mb: 3 }} />

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="inference tabs">
          <Tab label="メトリクス" id="tab-0" />
          <Tab label="結果" id="tab-1" />
          <Tab label="詳細" id="tab-2" />
        </Tabs>
      </Box>

      {/* メトリクスタブ */}
      {tabValue === 0 && (
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

      {/* 結果タブ */}
      {tabValue === 1 && (
        <>
          {isLoadingDetail || isLoadingResults ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : isErrorDetail || isErrorResults ? (
            <Alert severity="error" sx={{ mb: 3 }}>
              推論結果の取得中にエラーが発生しました。
            </Alert>
          ) : (
            <Grid container spacing={3}>
              {/* 基本情報 */}
              {inferenceDetail?.basic_info && (
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        基本情報
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={4} sm={3} md={2}>
                          <Typography variant="subtitle2">名前</Typography>
                        </Grid>
                        <Grid item xs={8} sm={9} md={10}>
                          <Typography variant="body1">{inferenceDetail.basic_info.name}</Typography>
                        </Grid>
                        
                        <Grid item xs={4} sm={3} md={2}>
                          <Typography variant="subtitle2">ステータス</Typography>
                        </Grid>
                        <Grid item xs={8} sm={9} md={10}>
                          <Chip
                            label={getStatusText(inferenceDetail.basic_info.status)}
                            size="small"
                            sx={{
                              backgroundColor: getStatusColor(inferenceDetail.basic_info.status),
                              color: 'white'
                            }}
                          />
                        </Grid>
                        
                        <Grid item xs={4} sm={3} md={2}>
                          <Typography variant="subtitle2">作成日</Typography>
                        </Grid>
                        <Grid item xs={8} sm={9} md={10}>
                          <Typography variant="body1">
                            {new Date(inferenceDetail.basic_info.created_at).toLocaleString()}
                          </Typography>
                        </Grid>
                        
                        {inferenceDetail.basic_info.completed_at && (
                          <>
                            <Grid item xs={4} sm={3} md={2}>
                              <Typography variant="subtitle2">完了日</Typography>
                            </Grid>
                            <Grid item xs={8} sm={9} md={10}>
                              <Typography variant="body1">
                                {new Date(inferenceDetail.basic_info.completed_at).toLocaleString()}
                              </Typography>
                            </Grid>
                          </>
                        )}
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              
              {/* モデル情報 */}
              {inferenceDetail?.model_info && (
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        モデル情報
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">プロバイダ</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.model_info.provider_name || '-'}</Typography>
                        </Grid>
                        
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">モデル</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.model_info.model_name || '-'}</Typography>
                        </Grid>
                        
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">最大トークン</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.model_info.max_tokens || '-'}</Typography>
                        </Grid>
                        
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">温度</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.model_info.temperature !== undefined ? inferenceDetail.model_info.temperature : '-'}</Typography>
                        </Grid>
                        
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">Top-P</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.model_info.top_p !== undefined ? inferenceDetail.model_info.top_p : '-'}</Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              
              {/* データセット情報 */}
              {inferenceDetail?.dataset_info && (
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        データセット情報
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">名前</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.dataset_info.name || '-'}</Typography>
                        </Grid>
                        
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">アイテム数</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.dataset_info.item_count || '-'}</Typography>
                        </Grid>
                        
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">サンプル数</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.dataset_info.sample_count || '-'}</Typography>
                        </Grid>
                        
                        <Grid item xs={4}>
                          <Typography variant="subtitle2">N-Shots</Typography>
                        </Grid>
                        <Grid item xs={8}>
                          <Typography variant="body1">{inferenceDetail.dataset_info.n_shots || 0}</Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              
              {/* 評価メトリクス */}
              {inferenceDetail?.evaluation_metrics && Object.keys(inferenceDetail.evaluation_metrics).length > 0 && (
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        評価メトリクス
                      </Typography>
                      <Grid container spacing={3}>
                        {Object.entries(inferenceDetail.evaluation_metrics).map(([key, value]) => (
                          <Grid item xs={12} sm={6} md={4} lg={3} key={key}>
                            <Paper elevation={2} sx={{ p: 2 }}>
                              <Typography variant="subtitle2" gutterBottom>
                                {key}
                              </Typography>
                              <Typography variant="h5" align="center">
                                {typeof value === 'number' ? value.toFixed(4) : value}
                              </Typography>
                            </Paper>
                          </Grid>
                        ))}
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              
              {/* メトリクス詳細データ */}
              {inferenceDetail?.metrics_details && Object.keys(inferenceDetail.metrics_details).length > 0 && (
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        詳細メトリクス
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        各メトリクスの詳細情報（サンプルごとの評価結果）
                      </Typography>
                      
                      {Object.entries(inferenceDetail.metrics_details).map(([metricName, metricDetails], index) => (
                        <Box key={index} sx={{ mb: 3 }}>
                          <Typography variant="subtitle1" gutterBottom>
                            {metricName.replace('_details', '')}
                          </Typography>
                          
                          {typeof metricDetails === 'object' && (
                            <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
                              <Table size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell>項目</TableCell>
                                    <TableCell>値</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {Object.entries(metricDetails as Record<string, any>).map(([key, value], i) => (
                                    <TableRow key={i}>
                                      <TableCell>{key}</TableCell>
                                      <TableCell>
                                        {typeof value === 'object' 
                                          ? JSON.stringify(value).slice(0, 100) + (JSON.stringify(value).length > 100 ? '...' : '')
                                          : typeof value === 'number' 
                                            ? value.toFixed(4) 
                                            : String(value)
                                        }
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          )}
                        </Box>
                      ))}
                    </CardContent>
                  </Card>
                </Grid>
              )}
              
              {/* 結果サマリー */}
              {inferenceDetail?.results_summary && (
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        結果サマリー
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={4} sm={3} md={2}>
                          <Typography variant="subtitle2">処理アイテム数</Typography>
                        </Grid>
                        <Grid item xs={8} sm={9} md={10}>
                          <Typography variant="body1">{inferenceDetail.results_summary.processed_items || 0}</Typography>
                        </Grid>
                        
                        <Grid item xs={4} sm={3} md={2}>
                          <Typography variant="subtitle2">成功数</Typography>
                        </Grid>
                        <Grid item xs={8} sm={9} md={10}>
                          <Typography variant="body1">{inferenceDetail.results_summary.success_count || 0}</Typography>
                        </Grid>
                        
                        <Grid item xs={4} sm={3} md={2}>
                          <Typography variant="subtitle2">エラー数</Typography>
                        </Grid>
                        <Grid item xs={8} sm={9} md={10}>
                          <Typography variant="body1">{inferenceDetail.results_summary.error_count || 0}</Typography>
                        </Grid>
                        
                        <Grid item xs={4} sm={3} md={2}>
                          <Typography variant="subtitle2">平均レイテンシ</Typography>
                        </Grid>
                        <Grid item xs={8} sm={9} md={10}>
                          <Typography variant="body1">
                            {inferenceDetail.results_summary.avg_latency ? `${inferenceDetail.results_summary.avg_latency.toFixed(2)}ms` : '-'}
                          </Typography>
                        </Grid>
                        
                        <Grid item xs={4} sm={3} md={2}>
                          <Typography variant="subtitle2">平均トークン数</Typography>
                        </Grid>
                        <Grid item xs={8} sm={9} md={10}>
                          <Typography variant="body1">
                            {inferenceDetail.results_summary.avg_tokens ? inferenceDetail.results_summary.avg_tokens.toFixed(2) : '-'}
                          </Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              
              {/* JSON結果データ */}
              {inferenceDetail?.json_results && (
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        詳細な評価結果
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        JSONファイルに保存された詳細な評価結果データ
                      </Typography>
                      
                      <Box sx={{ 
                        maxHeight: 400, 
                        overflow: 'auto',
                        backgroundColor: '#f5f5f5',
                        p: 2,
                        borderRadius: 1,
                        fontFamily: 'monospace',
                        fontSize: '0.85rem'
                      }}>
                        <pre>
                          {JSON.stringify(inferenceDetail.json_results, null, 2)}
                        </pre>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              
              {/* 結果リスト */}
              {results && results.length > 0 && (
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        結果アイテム
                      </Typography>
                      <TableContainer sx={{ maxHeight: 400 }}>
                        <Table stickyHeader sx={{ minWidth: 650 }} aria-label="推論結果テーブル">
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
                    </CardContent>
                  </Card>
                </Grid>
              )}
              
              {/* データがない場合 */}
              {(!inferenceDetail || (Object.keys(inferenceDetail).length === 0 && !results?.length)) && (
                <Grid item xs={12}>
                  <Paper sx={{ p: 3, textAlign: 'center' }}>
                    <Typography variant="body1" color="text.secondary">
                      {inference.status === 'pending'
                        ? '推論はまだ実行されていません。「実行」ボタンをクリックして推論を開始してください。'
                        : inference.status === 'running'
                          ? '推論を実行中です。結果が生成されるまでお待ちください。'
                          : '推論結果がありません。'}
                    </Typography>
                  </Paper>
                </Grid>
              )}
            </Grid>
          )}
        </>
      )}

      {/* 詳細タブ */}
      {tabValue === 2 && (
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
                    <Typography variant="body1">{model?.displayName || model?.name || inference.modelId}</Typography>
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
    </Box>
  );
};

export default InferenceDetail;