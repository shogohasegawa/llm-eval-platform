import React, { useState } from 'react';
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

  // 展開状態を管理
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  // データセット詳細の取得
  const {
    data: dataset,
    isLoading,
    isError,
    error,
  } = useDatasetByName(id || '');
  
  // サンプルデータとマージするための処理
  const enhancedDataset = React.useMemo(() => {
    if (!dataset) return null;
    
    // サンプルデータを使ってデータセットを拡張
    const sampleData = {
      instruction: '以下の質問に対して適切な回答を作成してください。',
      metrics: ['char_f1', 'exact_match'],
      output_length: 1024,
    };
    
    // 実際の実装では、実データを使用するためのロジックをここに追加
    // 今回はデモのため、サンプルデータを直接追加
    return {
      ...dataset,
      instruction: dataset.instruction || sampleData.instruction,
      metrics: dataset.metrics || sampleData.metrics,
      output_length: dataset.output_length || sampleData.output_length,
    };
  }, [dataset]);
  
  // デバッグ出力
  React.useEffect(() => {
    if (dataset) {
      console.log('元のデータセット:', dataset);
      console.log('拡張したデータセット:', enhancedDataset);
      
      if (enhancedDataset) {
        // サマリー表示の条件チェックをデバッグ
        const hasInstructions = !!enhancedDataset.instruction || enhancedDataset.items.some(item => item.instruction);
        const hasMetrics = !!enhancedDataset.metrics || enhancedDataset.items.some(item => item.additional_data?.metrics);
        const hasOutputLength = enhancedDataset.output_length !== undefined || enhancedDataset.items.some(item => item.additional_data?.output_length);
        
        console.log('データセットサマリー条件チェック:');
        console.log('- 指示あり:', hasInstructions);
        console.log('- メトリクスあり:', hasMetrics);
        console.log('- 出力長あり:', hasOutputLength);
        console.log('- サマリー表示条件:', hasInstructions || hasMetrics || hasOutputLength);
        
        // 各アイテムの詳細も確認
        console.log('アイテムの詳細:');
        enhancedDataset.items.forEach((item, index) => {
          console.log(`アイテム[${index}]:`, {
            id: item.id,
            has_instruction: !!item.instruction,
            has_metrics: !!item.additional_data?.metrics,
            has_output_length: !!item.additional_data?.output_length,
            additional_data: item.additional_data
          });
        });
      }
    }
  }, [dataset, enhancedDataset]);

  // エラーハンドリング
  if (error) {
    setError(`データセットの取得に失敗しました: ${error.message}`);
  }

  // 戻るボタンのハンドラ
  const handleGoBack = () => {
    navigate('/datasets');
  };

  // アイテムの展開/折りたたみを切り替える
  const toggleItemExpand = (itemId: string) => {
    setExpandedItems((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }));
  };

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
                      {/* データセットレベルの指示があれば表示 */}
                      {enhancedDataset.instruction && (
                        <Typography variant="body2" sx={{ mb: 1, whiteSpace: 'pre-wrap', fontWeight: 'bold' }}>
                          {enhancedDataset.instruction.length > 200 ? `${enhancedDataset.instruction.substring(0, 200)}...` : enhancedDataset.instruction}
                        </Typography>
                      )}
                      
                      {/* アイテムレベルの指示があれば表示 */}
                      {enhancedDataset.items.some(item => item.instruction) && 
                        Array.from(new Set(enhancedDataset.items
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

      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" component="h2" gutterBottom>
          データセットアイテム
        </Typography>
        
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          アイテム数: {enhancedDataset.items.length}
        </Typography>
        
        {/* パフォーマンス警告 */}
        {enhancedDataset.items.length > 100 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            このデータセットには {enhancedDataset.items.length} アイテムが含まれています。
            パフォーマンスを向上させるため、最初の 50 アイテムのみを表示しています。
          </Alert>
        )}
      </Box>

      <Grid container spacing={3}>
        {enhancedDataset.items.slice(0, 50).map((item: DatasetItem) => (
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
                    入力
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f8f9fa', whiteSpace: 'pre-wrap' }}>
                    {item.instruction ? (
                      <>
                        <Typography variant="subtitle2" color="primary.dark" gutterBottom>
                          指示:
                        </Typography>
                        <Typography paragraph>{truncateText(item.instruction, 500)}</Typography>
                        <Divider sx={{ my: 1 }} />
                        <Typography variant="subtitle2" color="primary.dark" gutterBottom>
                          入力内容:
                        </Typography>
                        {truncateText(item.input, 500)}
                      </>
                    ) : (
                      truncateText(item.input, 500)
                    )}
                  </Paper>
                </Box>
              ) : item.instruction ? (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    指示
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f8f9fa', whiteSpace: 'pre-wrap' }}>
                    {truncateText(item.instruction, 500)}
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
                    {truncateText(item.output, 500)}
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
                    <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f0f0f0', overflow: 'auto', maxHeight: '200px' }}>
                      <pre>
                        {formatJson(
                          Object.fromEntries(
                            Object.entries(item.additional_data)
                              .filter(([key]) => !['metrics', 'output_length'].includes(key))
                          )
                        ).substring(0, 1000) + (
                          formatJson(
                            Object.fromEntries(
                              Object.entries(item.additional_data)
                                .filter(([key]) => !['metrics', 'output_length'].includes(key))
                            )
                          ).length > 1000 ? "..." : ""
                        )}
                      </pre>
                    </Paper>
                  )}
                </Box>
              )}
            </Paper>
          </Grid>
        ))}
        
        {/* 表示の制限を超えるアイテム数がある場合 */}
        {enhancedDataset.items.length > 50 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3, textAlign: 'center', borderStyle: 'dashed' }}>
              <Typography variant="body1" color="text.secondary">
                表示制限: 合計 {enhancedDataset.items.length} アイテム中 50 アイテムを表示しています。
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                大量のアイテムを含むデータセットはパフォーマンスに影響する可能性があります。
              </Typography>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default DatasetDetail;
