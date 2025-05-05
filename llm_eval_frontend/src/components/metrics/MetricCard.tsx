import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Button, 
  Chip, 
  Stack, 
  IconButton 
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { Metric } from '../../types/metrics';

interface MetricCardProps {
  metric: Metric;
  onEdit: (metric: Metric) => void;
  onDelete: (metricId: string) => void;
}

/**
 * 評価指標情報を表示するカードコンポーネント
 */
const MetricCard: React.FC<MetricCardProps> = ({ metric, onEdit, onDelete }) => {
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
      case 'semantic_similarity':
        return '#9C27B0';
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
            <IconButton size="small" onClick={() => onEdit(metric)} aria-label="編集">
              <EditIcon fontSize="small" />
            </IconButton>
            <IconButton 
              size="small" 
              onClick={() => onDelete(metric.id)} 
              aria-label="削除"
              color="error"
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
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
            label={metric.isHigherBetter ? '高いほど良い' : '低いほど良い'} 
            size="small" 
            variant="outlined"
          />
        </Box>
        
        {metric.description && (
          <Typography variant="body2" color="text.secondary" mb={2}>
            {metric.description}
          </Typography>
        )}
        
        {metric.parameters && Object.keys(metric.parameters).length > 0 && (
          <Box mt={2}>
            <Typography variant="subtitle2" gutterBottom>
              パラメータ:
            </Typography>
            {Object.entries(metric.parameters).map(([key, value]) => (
              <Typography key={key} variant="body2" color="text.secondary">
                {key}: {typeof value === 'object' ? JSON.stringify(value) : value}
              </Typography>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default MetricCard;
