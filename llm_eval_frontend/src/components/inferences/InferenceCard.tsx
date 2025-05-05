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
  LinearProgress
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
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
  const showRunButton = inference.status === 'pending' || inference.status === 'failed';
  
  // 停止ボタンの表示条件
  const showStopButton = inference.status === 'running';

  return (
    <Card 
      sx={{ 
        mb: 2, 
        height: '100%',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6" component="div">
            {inference.name}
          </Typography>
          <Stack direction="row" spacing={1}>
            <IconButton size="small" onClick={() => onView(inference)} aria-label="表示">
              <VisibilityIcon fontSize="small" />
            </IconButton>
            {showRunButton && (
              <IconButton 
                size="small" 
                onClick={() => onRun(inference)} 
                aria-label="実行"
                color="primary"
              >
                <PlayArrowIcon fontSize="small" />
              </IconButton>
            )}
            {showStopButton && (
              <IconButton 
                size="small" 
                onClick={() => onStop(inference)} 
                aria-label="停止"
                color="warning"
              >
                <StopIcon fontSize="small" />
              </IconButton>
            )}
            <IconButton 
              size="small" 
              onClick={() => onDelete(inference.id)} 
              aria-label="削除"
              color="error"
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Box>
        
        <Box display="flex" alignItems="center" mb={2}>
          <Chip 
            label={getStatusText(inference.status)} 
            size="small" 
            sx={{ 
              backgroundColor: getStatusColor(inference.status),
              color: 'white',
              mr: 1
            }} 
          />
          <Typography variant="body2" color="text.secondary">
            {inference.results.length} 結果
          </Typography>
        </Box>
        
        {inference.description && (
          <Typography variant="body2" color="text.secondary" mb={2}>
            {inference.description}
          </Typography>
        )}
        
        {inference.status === 'running' && (
          <Box sx={{ width: '100%', mb: 2 }}>
            <LinearProgress variant="determinate" value={inference.progress} />
            <Typography variant="body2" color="text.secondary" align="right" mt={0.5}>
              {inference.progress}%
            </Typography>
          </Box>
        )}
        
        <Box mt={2}>
          <Typography variant="body2" color="text.secondary">
            データセット: {inference.datasetId}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            プロバイダ: {inference.providerId}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            モデル: {inference.modelId}
          </Typography>
        </Box>
        
        <Box mt={2} display="flex" justifyContent="flex-end">
          <Button 
            variant="outlined" 
            size="small" 
            onClick={() => onView(inference)}
          >
            詳細を表示
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default InferenceCard;
