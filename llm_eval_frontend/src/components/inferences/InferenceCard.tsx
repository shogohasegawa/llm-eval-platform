import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Button, 
  Chip, 
  Stack, 
  IconButton,
  LinearProgress,
  Tooltip,
  Divider,
  Grid
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import UpdateIcon from '@mui/icons-material/Update';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { Inference } from '../../types/inference';

interface InferenceCardProps {
  inference: Inference;
  onRun: (inference: Inference) => void;
  onStop: (inference: Inference) => void;
  onDelete: (inferenceId: string) => void;
  onView: (inference: Inference) => void;
}

/**
 * 推論情報を表示するカードコンポーネント
 */
const InferenceCard: React.FC<InferenceCardProps> = ({ inference, onRun, onStop, onDelete, onView }) => {
  // 日付をフォーマットする関数
  const formatDate = (dateString: string | Date | undefined): string => {
    if (!dateString) return '未記録';
    
    try {
      // 日付文字列またはDateオブジェクトを処理
      const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
      
      if (isNaN(date.getTime())) {
        return '無効な日付';
      }
      
      // 日付フォーマット - バックエンド側で既にJST時間で保存されているので変換不要
      const formatted = date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
      
      return formatted;
    } catch (err) {
      console.error('日付のフォーマットエラー:', err);
      return '日付エラー';
    }
  };
  
  // 推論ステータスに応じた色を設定（エラーがある場合は考慮）
  const getStatusColor = (status: string, hasError: boolean = false) => {
    // エラーがある場合は、状態に関わらず警告色や失敗色を使用
    if (hasError) {
      return status === 'completed' ? '#FF9800' : '#F44336'; // 完了でもエラーならオレンジ、それ以外なら赤
    }
    
    switch (status) {
      case 'pending':
        return '#757575'; // グレー
      case 'running':
        return '#2196F3'; // 青
      case 'completed':
        return '#4CAF50'; // 緑
      case 'failed':
        return '#F44336'; // 赤
      default:
        return '#757575'; // デフォルトはグレー
    }
  };

  // 推論ステータスに応じた表示テキストを設定（エラーがある場合は考慮）
  const getStatusText = (status: string, hasError: boolean = false) => {
    // エラーがある場合は、状態に表示を上書き
    if (hasError) {
      return status === 'completed' ? '完了(警告)' : '失敗';
    }
    
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
  const showRunButton = inference.status === 'pending' || inference.status === 'failed';
  
  // 停止ボタンの表示条件
  const showStopButton = inference.status === 'running';
  
  // エラー状態を判定
  const hasError = Boolean(inference.error) || 
                   (inference.status === 'completed' && 
                    (inference.metrics === null || 
                     (inference.metrics && Object.keys(inference.metrics).length === 0)));
                     
  // エラー内容を取得
  const errorMessage = inference.error || 
                      (hasError && inference.status === 'completed' ? 
                       "メトリクスが取得できませんでした" : null);
  
  // 日付情報の処理
  const createdAt = formatDate(inference.createdAt);
  const updatedAt = formatDate(inference.updatedAt);
  const completedAt = inference.completedAt ? formatDate(inference.completedAt) : null;

  return (
    <Card 
      sx={{ 
        mb: 1,
        width: '100%',
        display: 'flex',
        flexDirection: 'column'
      }}
      variant="outlined"
    >
      <CardContent sx={{ p: 1, py: 1, '&:last-child': { pb: 1 } }}>
        <Grid container spacing={1} alignItems="center">
          {/* 左側：ステータスインジケーターとタイトル */}
          <Grid item xs={12} md={4}>
            <Box display="flex" alignItems="center">
              <Chip 
                label={getStatusText(inference.status, hasError)} 
                size="small" 
                sx={{ 
                  backgroundColor: getStatusColor(inference.status, hasError),
                  color: 'white',
                  mr: 2,
                  minWidth: 70
                }} 
              />
              <Box>
                <Typography variant="subtitle1" component="div" sx={{ fontWeight: 'bold' }}>
                  {inference.name}
                </Typography>
                {inference.description && (
                  <Typography variant="caption" color="text.secondary">
                    {inference.description}
                  </Typography>
                )}
              </Box>
            </Box>
          </Grid>
          
          {/* 中央：進捗バーとメタデータ */}
          <Grid item xs={12} md={5}>
            <Box>
              {/* データセット・モデル情報 */}
              <Box display="flex" flexWrap="wrap" gap={1}>
                <Chip 
                  size="small" 
                  label={`データセット: ${inference.datasetId ? 
                    (inference.datasetId.includes('/') ? 
                      inference.datasetId.split('/').pop()?.replace('.json', '') : 
                      inference.datasetId) : 
                    '不明'}`} 
                  variant="outlined" 
                />
                <Chip size="small" label={`モデル: ${inference.modelName || inference.modelId || '不明'}`} variant="outlined" />
                <Chip size="small" label={`プロバイダ: ${inference.providerName || inference.providerId || '不明'}`} variant="outlined" />
                <Chip size="small" label={`結果: ${inference.results?.length || 0}件`} variant="outlined" />
                {inference.status === 'completed' && (
                  <Chip 
                    size="small" 
                    label={`メトリクス: ${inference.metrics && Object.keys(inference.metrics).length > 0 ? '取得済' : '未取得'}`} 
                    variant="outlined"
                    color={inference.metrics && Object.keys(inference.metrics).length > 0 ? 'success' : 'error'}
                  />
                )}
              </Box>
              
              {/* 進捗バー */}
              {inference.status === 'running' && (
                <Box sx={{ width: '100%', mt: 1 }}>
                  <LinearProgress 
                    variant="indeterminate" 
                    color="primary"
                    sx={{ height: 4, borderRadius: 2 }}
                  />
                  <Typography variant="caption" color="primary" align="right" fontWeight="bold">
                    処理中...
                  </Typography>
                </Box>
              )}
              
              {inference.status === 'pending' && (
                <Box sx={{ width: '100%', mt: 1 }}>
                  <LinearProgress 
                    variant="indeterminate" 
                    color="secondary"
                    sx={{ height: 4, borderRadius: 2 }}
                  />
                  <Typography variant="caption" color="text.secondary" align="right">
                    待機中...
                  </Typography>
                </Box>
              )}
              
              {/* エラー表示を強化 - 完了していてもエラーがある場合に表示 */}
              {hasError && errorMessage && (
                <Box sx={{ width: '100%', mt: 1, p: 0.5, bgcolor: '#ffebee', borderRadius: 1 }}>
                  <Typography variant="caption" color="error" fontWeight="bold">
                    エラー: {errorMessage}
                  </Typography>
                  {inference.status === 'completed' && !inference.metrics && (
                    <Typography variant="caption" color="error" display="block">
                      推論は完了しましたが、メトリクスの計算中にエラーが発生した可能性があります。
                    </Typography>
                  )}
                </Box>
              )}
            </Box>
          </Grid>
          
          {/* 右側：アクションボタンと日付 */}
          <Grid item xs={12} md={3}>
            <Box display="flex" flexDirection="column" alignItems="flex-end">
              {/* アクションボタン */}
              <Stack direction="row" spacing={1} mb={1}>
                <Tooltip title="詳細を表示">
                  <IconButton size="small" onClick={() => onView(inference)} color="primary">
                    <VisibilityIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                
                {showRunButton && (
                  <Tooltip title="実行">
                    <IconButton size="small" onClick={() => onRun(inference)} color="primary">
                      <PlayArrowIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
                
                {showStopButton && (
                  <Tooltip title="停止">
                    <IconButton size="small" onClick={() => onStop(inference)} color="warning">
                      <StopIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
                
                <Tooltip title="削除">
                  <IconButton size="small" onClick={() => onDelete(inference.id)} color="error">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Stack>
              
              {/* 日付情報 */}
              <Typography variant="caption" color="text.secondary" align="right" sx={{ fontSize: '0.7rem' }}>
                作成: {createdAt}
              </Typography>
              
              {completedAt && (
                <Typography variant="caption" color="success.main" align="right" sx={{ fontSize: '0.7rem' }}>
                  完了: {completedAt}
                </Typography>
              )}
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default InferenceCard;
