import React, { useState } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Button, 
  Chip, 
  Stack, 
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle
} from '@mui/material';
import CodeIcon from '@mui/icons-material/Code';
import DeleteIcon from '@mui/icons-material/Delete';
import { Metric } from '../../types/metrics';

interface MetricCardProps {
  metric: Metric;
  onEdit?: (metric: Metric) => void;
  onDelete?: (metricId: string) => void;
  onViewCode?: (metricName: string) => void;
}

/**
 * 評価指標情報を表示するカードコンポーネント
 */
const MetricCard: React.FC<MetricCardProps> = ({ metric, onEdit, onDelete, onViewCode }) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (onDelete) {
      onDelete(metric.name);
    }
    setDeleteDialogOpen(false);
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
  };

  // 評価指標タイプに応じた色を設定
  const getMetricTypeColor = (type: string) => {
    switch (type) {
      case 'accuracy':
      case 'precision':
      case 'recall':
      case 'f1':
        return '#4CAF50';
      case 'bleu':
      case 'rouge':
        return '#2196F3';
      case 'exact_match':
      case 'exact_match_figure':
      case 'semantic_similarity':
      case 'contains_answer':
        return '#9C27B0';
      case 'char_f1':
      case 'set_f1':
        return '#3F51B5';
      case 'latency':
      case 'token_count':
        return '#FF9800';
      case 'custom':
        return '#607D8B';
      default:
        return '#757575';
    }
  };

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
            {metric.name}
          </Typography>
          <Stack direction="row" spacing={1}>
            {onViewCode && (
              <IconButton 
                size="small" 
                onClick={() => onViewCode(metric.name)} 
                aria-label="コードを表示"
                color="primary"
              >
                <CodeIcon fontSize="small" />
              </IconButton>
            )}
            {onDelete && metric.is_custom && (
              <IconButton 
                size="small" 
                onClick={handleDeleteClick} 
                aria-label="削除"
                color="error"
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            )}
          </Stack>
        </Box>
        
        <Box display="flex" alignItems="center" mb={2}>
          <Chip 
            label={metric.type} 
            size="small" 
            sx={{ 
              backgroundColor: getMetricTypeColor(metric.type),
              color: 'white',
              mr: 1
            }} 
          />
          <Chip 
            label={metric.isHigherBetter === true ? '高いほど良い' : '低いほど良い'} 
            size="small" 
            variant="outlined"
            color={metric.isHigherBetter === true ? "success" : "warning"}
          />
          {/* デバッグ情報（表示を有効化） */}
          <div style={{ fontSize: '9px', color: '#999', marginTop: '4px' }}>
            isHigherBetter: {String(metric.isHigherBetter)} (type: {typeof metric.isHigherBetter})
            <br />
            is_higher_better: {String(metric.is_higher_better)} (type: {typeof metric.is_higher_better})
            <br />
            Raw JSON: {JSON.stringify({isHigherBetter: metric.isHigherBetter, is_higher_better: metric.is_higher_better})}
          </div>
        </Box>
        
        {metric.description && (
          <Typography variant="body2" color="text.secondary" mb={2}>
            {metric.description}
          </Typography>
        )}
        
        {metric.parameters && Object.keys(metric.parameters).length > 0 && (
          <Box mt={2} sx={{ backgroundColor: '#f5f5f5', p: 1.5, borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              パラメータ:
            </Typography>
            <Box sx={{ 
              fontFamily: 'monospace', 
              fontSize: '0.85rem',
              backgroundColor: '#f8f8f8',
              p: 1,
              borderRadius: 1,
              border: '1px solid #e0e0e0',
              maxHeight: '100px',
              overflow: 'auto'
            }}>
              {JSON.stringify(metric.parameters, null, 2)}
            </Box>
          </Box>
        )}
      </CardContent>

      {/* 削除確認ダイアログ */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          評価指標の削除
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            評価指標「{metric.name}」を削除しますか？この操作は元に戻せません。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} color="primary">
            キャンセル
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" autoFocus>
            削除
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default MetricCard;
