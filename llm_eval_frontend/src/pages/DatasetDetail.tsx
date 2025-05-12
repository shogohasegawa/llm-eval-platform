import React, { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Card,
  CardContent,
  Grid,
  Divider,
  CircularProgress,
  Alert,
  Badge,
  Pagination,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { useDatasetByName } from '../hooks/useDatasets';
import { DatasetItem } from '../types/dataset';
import { useAppContext } from '../contexts/AppContext';

/**
 * データセット詳細ページコンポーネント
 */
const DatasetDetail: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { setError } = useAppContext();
  const [searchParams] = React.useState(() => new URLSearchParams(window.location.search));
  const datasetType = searchParams.get('type');

  // 展開状態を管理
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});
  // ページネーション状態を管理
  const [page, setPage] = useState(1);
  const itemsPerPage = 50;

  // データセット詳細の取得 - 名前とタイプの両方を指定
  const {
    data: dataset,
    isLoading,
    isError,
    error,
  } = useDatasetByName(id || '', datasetType || undefined);
  
  // バックエンドから受け取ったデータセットをそのまま使用
  const enhancedDataset = dataset;

  // エラーハンドリング
  if (error) {
    setError(`データセットの取得に失敗しました: ${error.message}`);
  }

  // 戻るボタンのハンドラ - 元のタブを保持
  const handleGoBack = () => {
    // タイプがあれば戻り先でも対応するタブを表示
    const tabParam = datasetType ? `?tab=${datasetType}` : '';
    navigate(`/datasets${tabParam}`);
  };

  // アイテムの展開/折りたたみを切り替える
  const toggleItemExpand = (itemId: string) => {
    setExpandedItems((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }));
  };
  
  // ページ変更ハンドラ
  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    // ページ変更時にスクロールを上部に戻す
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  
  // 現在のページに表示するアイテムを取得
  const paginatedItems = useMemo(() => {
    if (!enhancedDataset) return [];
    const startIndex = (page - 1) * itemsPerPage;
    return enhancedDataset.items.slice(startIndex, startIndex + itemsPerPage);
  }, [enhancedDataset, page, itemsPerPage]);

  // データセットタイプに応じた色を設定
  const getDatasetTypeColor = (type: string) => {
    switch (type) {
      case 'test':
        return '#4CAF50';
      case 'n_shot':
        return '#2196F3';
      default:
        return '#757575';
    }
  };

  // JSONを整形して表示
  const formatJson = (value: any) => {
    if (!value) return '';
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  // テキストを省略表示
  const truncateText = (text: string | undefined, maxLength: number) => {
    if (!text) return '-';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" my={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (isError || !dataset || !enhancedDataset) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          データセットの取得中にエラーが発生したか、データセットが見つかりませんでした。
        </Alert>
        <Box mt={2}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleGoBack}
          >
            データセット一覧に戻る
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" alignItems="center" mb={3}>
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={handleGoBack}
          sx={{ mr: 2 }}
        >
          戻る
        </Button>
        <Typography variant="h4" component="h1">
          {enhancedDataset.name}
        </Typography>
      </Box>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Box mb={2}>
                <Typography variant="h6" component="div" gutterBottom>
                  基本情報
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  <strong>名前:</strong> {enhancedDataset.name}
                </Typography>
                {enhancedDataset.description && (
                  <Typography variant="body2" color="text.secondary" paragraph>
                    <strong>説明:</strong> {enhancedDataset.description}
                  </Typography>
                )}
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" color="text.secondary" component="span">
                    <strong>タイプ:</strong>{' '}
                  </Typography>
                  <Chip
                    label={enhancedDataset.type}
                    size="small"
                    sx={{
                      backgroundColor: getDatasetTypeColor(enhancedDataset.type),
                      color: 'white',
                    }}
                  />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  <strong>アイテム数:</strong> {enhancedDataset.itemCount || enhancedDataset.item_count}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box mb={2}>
                <Typography variant="h6" component="div" gutterBottom>
                  ファイル情報
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  <strong>ファイルパス:</strong> {enhancedDataset.file_path}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>作成日時:</strong>{' '}
                  {new Date(enhancedDataset.created_at || enhancedDataset.createdAt || '').toLocaleString()}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      {/* データセットの共通指示・メトリクス・出力長情報 */}
      {(enhancedDataset.instruction || 
        enhancedDataset.metrics || 
        enhancedDataset.output_length ||
        enhancedDataset.items.some(item => item.instruction) || 
        enhancedDataset.items.some(item => item.additional_data?.metrics) || 
        enhancedDataset.items.some(item => item.additional_data?.output_length)) && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" component="div" gutterBottom>
              データセット情報サマリー
            </Typography>
            <Grid container spacing={3}>
              {/* 指示情報 */}
              {(enhancedDataset.instruction || enhancedDataset.items.some(item => item.instruction)) && (
                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                    <Typography variant="subtitle1" color="primary.dark" gutterBottom>
                      共通指示パターン
                    </Typography>
                    <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
                      {/* データセットレベルの指示があれば表示、なければ「指示なし」と表示 */}
                      {enhancedDataset.instruction ? (
                        <Typography variant="body2" sx={{ mb: 1, whiteSpace: 'pre-wrap', fontWeight: 'bold' }}>
                          {enhancedDataset.instruction.length > 200 ? `${enhancedDataset.instruction.substring(0, 200)}...` : enhancedDataset.instruction}
                        </Typography>
                      ) : (
                        <Typography variant="body2" sx={{ mb: 1, fontStyle: 'italic', color: 'text.secondary' }}>
                          データセットレベルの指示はありません
                        </Typography>
                      )}
                      
                      {/* アイテムレベルの指示があれば表示 */}
                      {enhancedDataset.items.some(item => item.instruction) ? (
                        <>
                          <Typography variant="subtitle2" sx={{ mt: 2, mb: 1, color: 'text.secondary' }}>
                            アイテムレベルの指示例:
                          </Typography>
                          {Array.from(new Set(enhancedDataset.items
                            .filter(item => item.instruction)
                            .map(item => item.instruction)
                            .slice(0, 3)))
                            .map((instruction, idx) => (
                              <Typography key={idx} variant="body2" sx={{ mb: 1, whiteSpace: 'pre-wrap' }}>
                                {instruction.length > 200 ? `${instruction.substring(0, 200)}...` : instruction}
                              </Typography>
                            ))}
                          {enhancedDataset.items.filter(item => item.instruction).length > 3 && (
                            <Typography variant="body2" color="text.secondary">
                              ...他 {enhancedDataset.items.filter(item => item.instruction).length - 3} 件
                            </Typography>
                          )}
                        </>
                      ) : !enhancedDataset.instruction && (
                        <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                          アイテムレベルの指示もありません
                        </Typography>
                      )}
                    </Box>
                  </Paper>
                </Grid>
              )}

              {/* メトリクス情報 */}
              {(enhancedDataset.metrics || enhancedDataset.items.some(item => item.additional_data?.metrics)) && (
                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                    <Typography variant="subtitle1" color="secondary.dark" gutterBottom>
                      メトリクス情報
                    </Typography>
                    {(() => {
                      // メトリクスの種類を集計
                      const metricsTypes = new Set<string>();
                      
                      // データセットレベルのメトリクスを追加
                      if (enhancedDataset.metrics) {
                        if (Array.isArray(enhancedDataset.metrics)) {
                          enhancedDataset.metrics.forEach(metric => metricsTypes.add(metric));
                        } else if (typeof enhancedDataset.metrics === 'object') {
                          Object.keys(enhancedDataset.metrics).forEach(key => metricsTypes.add(key));
                        } else if (typeof enhancedDataset.metrics === 'string') {
                          metricsTypes.add(enhancedDataset.metrics);
                        }
                      }
                      
                      // アイテムレベルのメトリクスを追加
                      const metricsValues: Record<string, number[]> = {};
                      
                      enhancedDataset.items.forEach(item => {
                        if (item.additional_data?.metrics) {
                          const metrics = item.additional_data.metrics;
                          if (typeof metrics === 'object') {
                            Object.entries(metrics).forEach(([key, value]) => {
                              metricsTypes.add(key);
                              if (typeof value === 'number') {
                                if (!metricsValues[key]) metricsValues[key] = [];
                                metricsValues[key].push(value);
                              }
                            });
                          }
                        }
                      });
                      
                      // 平均値を計算
                      const metricsAvg: Record<string, number> = {};
                      Object.entries(metricsValues).forEach(([key, values]) => {
                        if (values.length > 0) {
                          metricsAvg[key] = values.reduce((sum, val) => sum + val, 0) / values.length;
                        }
                      });
                      
                      return (
                        <Box>
                          <Typography variant="body2" paragraph>
                            <strong>使用メトリクス:</strong> {Array.from(metricsTypes).join(', ')}
                          </Typography>
                          {Object.entries(metricsAvg).length > 0 && (
                            <Box>
                              <Typography variant="body2" gutterBottom>
                                <strong>平均値:</strong>
                              </Typography>
                              {Object.entries(metricsAvg).map(([key, value]) => (
                                <Typography key={key} variant="body2">
                                  {key}: {value.toFixed(2)}
                                </Typography>
                              ))}
                            </Box>
                          )}
                        </Box>
                      );
                    })()}
                  </Paper>
                </Grid>
              )}

              {/* 出力長情報 */}
              {(enhancedDataset.output_length !== undefined || enhancedDataset.items.some(item => item.additional_data?.output_length)) && (
                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                    <Typography variant="subtitle1" color="info.dark" gutterBottom>
                      出力長情報
                    </Typography>
                    {(() => {
                      // データセットレベルの出力長
                      let datasetOutputLength = typeof enhancedDataset.output_length === 'number' ? enhancedDataset.output_length : null;
                      
                      // アイテムレベルの出力長
                      const outputLengths = enhancedDataset.items
                        .filter(item => item.additional_data?.output_length !== undefined)
                        .map(item => item.additional_data!.output_length as number);
                      
                      if (outputLengths.length === 0 && datasetOutputLength === null) return null;
                      
                      // アイテムレベルの統計情報
                      let avgLength = 0;
                      let minLength = 0;
                      let maxLength = 0;
                      
                      if (outputLengths.length > 0) {
                        avgLength = outputLengths.reduce((sum, len) => sum + len, 0) / outputLengths.length;
                        minLength = Math.min(...outputLengths);
                        maxLength = Math.max(...outputLengths);
                      }
                      
                      return (
                        <Box>
                          {datasetOutputLength !== null && (
                            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                              <strong>設定出力長:</strong> {datasetOutputLength}
                            </Typography>
                          )}
                          
                          {outputLengths.length > 0 && (
                            <>
                              <Typography variant="body2">
                                <strong>平均出力長:</strong> {avgLength.toFixed(0)}
                              </Typography>
                              <Typography variant="body2">
                                <strong>最小出力長:</strong> {minLength}
                              </Typography>
                              <Typography variant="body2">
                                <strong>最大出力長:</strong> {maxLength}
                              </Typography>
                            </>
                          )}
                        </Box>
                      );
                    })()}
                  </Paper>
                </Grid>
              )}
            </Grid>
          </CardContent>
        </Card>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" component="h2">
          データセットアイテム
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {enhancedDataset.items.length > 0 
            ? `${(page - 1) * itemsPerPage + 1}-${Math.min(page * itemsPerPage, enhancedDataset.items.length)}件 / 全${enhancedDataset.items.length}件`
            : '0件'
          }
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {paginatedItems.map((item: DatasetItem) => (
          <Grid item xs={12} key={item.id}>
            <Paper 
              sx={{ 
                p: 3, 
                borderRadius: 2,
                boxShadow: 2,
                position: 'relative',
                overflow: 'hidden',
                '&:before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '4px',
                  height: '100%',
                  backgroundColor: (theme) => theme.palette.primary.main
                }
              }}
            >
              {/* ヘッダー情報 */}
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={12} md={4}>
                  <Typography variant="overline" color="primary">
                    アイテム ID: {item.id}
                  </Typography>
                </Grid>
                
                {/* メトリクス情報（存在する場合） */}
                {item.additional_data?.metrics && (
                  <Grid item xs={12} md={4}>
                    <Typography variant="overline" color="secondary">
                      メトリクス: {
                        typeof item.additional_data.metrics === 'object' 
                          ? Object.entries(item.additional_data.metrics)
                              .map(([key, value]) => `${key}: ${typeof value === 'number' ? value.toFixed(2) : value}`)
                              .join(', ')
                          : String(item.additional_data.metrics)
                      }
                    </Typography>
                  </Grid>
                )}
                
                {/* 出力長情報（存在する場合） */}
                {item.additional_data?.output_length && (
                  <Grid item xs={12} md={4}>
                    <Typography variant="overline" color="info.main">
                      出力長: {item.additional_data.output_length}
                    </Typography>
                  </Grid>
                )}
              </Grid>
              
              {/* 入力（以前の指示を含む） */}
              {item.input && item.input.trim() ? (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    {dataset?.display_config?.file_format === 'jsonl' ? dataset?.display_config?.labels?.primary : '入力'}
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f8f9fa', whiteSpace: 'pre-wrap' }}>
                    {item.instruction ? (
                      <>
                        {/* 1ターン目 (instruction) */}
                        <Typography variant="subtitle2" color="primary.dark" gutterBottom>
                          {dataset?.display_config?.file_format === 'jsonl' ? dataset?.display_config?.labels?.secondary + ':' : '指示:'}
                        </Typography>
                        <Typography paragraph>{item.instruction}</Typography>

                        {/* 2ターン目 (input) - 従来の互換性のため */}
                        {item.input && (
                          <>
                            <Divider sx={{ my: 1 }} />
                            <Typography variant="subtitle2" color="primary.dark" gutterBottom>
                              {dataset?.display_config?.file_format === 'jsonl' ? dataset?.display_config?.labels?.tertiary + ':' : '入力内容:'}
                            </Typography>
                            <Typography paragraph>{item.input}</Typography>
                          </>
                        )}

                        {/* 3ターン目以降 - additional_dataのturn_dataを使用 */}
                        {item.additional_data?.turn_data && Array.isArray(item.additional_data.turn_data) &&
                         item.additional_data.turn_data.length > 2 &&
                         item.additional_data.turn_data.slice(2).map((turnText, turnIndex) => (
                          <React.Fragment key={turnIndex + 2}>
                            <Divider sx={{ my: 1 }} />
                            <Typography variant="subtitle2" color="primary.dark" gutterBottom>
                              {/* 3ターン目以降は動的に生成 */}
                              {dataset?.display_config?.file_format === 'jsonl'
                                ? `質問(${turnIndex + 3}ターン目):`
                                : `入力(${turnIndex + 3}):`}
                            </Typography>
                            <Typography paragraph>{turnText}</Typography>
                          </React.Fragment>
                        ))}
                      </>
                    ) : (
                      item.input
                    )}
                  </Paper>
                </Box>
              ) : item.instruction ? (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    {dataset?.display_config?.file_format === 'jsonl' ? dataset?.display_config?.labels?.secondary : '指示'}
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f8f9fa', whiteSpace: 'pre-wrap' }}>
                    {item.instruction}
                  </Paper>
                </Box>
              ) : null}
              
              {/* 出力 */}
              {item.output && item.output.trim() && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom color="secondary">
                    出力
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#fcf8e3', whiteSpace: 'pre-wrap' }}>
                    {item.output}
                  </Paper>
                </Box>
              )}
              
              {/* 追加データ */}
              {item.additional_data && 
               Object.keys(item.additional_data)
                .filter(key => !['metrics', 'output_length'].includes(key))
                .length > 0 && (
                <Box>
                  <Typography 
                    variant="subtitle1" 
                    fontWeight="bold" 
                    gutterBottom
                    sx={{ display: 'flex', alignItems: 'center' }}
                  >
                    <IconButton
                      onClick={() => toggleItemExpand(item.id)}
                      size="small"
                      sx={{ mr: 1 }}
                    >
                      {expandedItems[item.id] ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                    追加データ
                  </Typography>
                  
                  {expandedItems[item.id] && (
                    <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f0f0f0', overflow: 'auto' }}>
                      <pre>
                        {formatJson(
                          Object.fromEntries(
                            Object.entries(item.additional_data)
                              .filter(([key]) => !['metrics', 'output_length'].includes(key))
                          )
                        )}
                      </pre>
                    </Paper>
                  )}
                </Box>
              )}
            </Paper>
          </Grid>
        ))}
      </Grid>
      
      {enhancedDataset.items.length > itemsPerPage && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <Pagination 
            count={Math.ceil(enhancedDataset.items.length / itemsPerPage)} 
            page={page} 
            onChange={handlePageChange}
            color="primary"
            size="large"
            showFirstButton
            showLastButton
          />
        </Box>
      )}
    </Box>
  );
};

export default DatasetDetail;
