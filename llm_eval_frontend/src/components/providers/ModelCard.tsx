import React from 'react';
import { 
  Box, 
  Typography, 
  Card, 
  CardContent, 
  Grid, 
  Chip,
  IconButton,
  Tooltip,
  Stack,
  Button
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import StorageIcon from '@mui/icons-material/Storage';
import HttpIcon from '@mui/icons-material/Http';
import KeyIcon from '@mui/icons-material/Key';
import { Model } from '../../types/provider';
import { useProvider } from '../../hooks/useProviders';

interface ModelCardProps {
  model: Model;
  onSelect?: (model: Model) => void;
  onEdit?: (model: Model) => void;
  onDelete?: (model: Model) => void;
}

/**
 * モデル情報を表示するカードコンポーネント
 */
const ModelCard: React.FC<ModelCardProps> = ({ 
  model, 
  onSelect, 
  onEdit, 
  onDelete 
}) => {
  // プロバイダ情報を取得
  const { data: provider } = useProvider(model.providerId);

  const handleClick = () => {
    if (onSelect) {
      onSelect(model);
    }
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit) {
      onEdit(model);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete && confirm('このモデルを削除してもよろしいですか？')) {
      onDelete(model);
    }
  };

  // エンドポイントとAPIキーの表示用に加工
  const truncatedEndpoint = model.endpoint ? 
    model.endpoint.length > 30 ? 
      model.endpoint.substring(0, 27) + '...' : 
      model.endpoint : 
    '未設定';
  
  const hasApiKey = model.apiKey && model.apiKey.length > 0;

  return (
    <Card 
      sx={{ 
        cursor: onSelect ? 'pointer' : 'default',
        transition: 'all 0.2s',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: 3
        },
        height: '100%',
        display: 'flex',
        flexDirection: 'column'
      }}
      onClick={handleClick}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6" component="div" noWrap>
            {model.displayName}
          </Typography>
          <Stack direction="row" spacing={1}>
            {model.description && (
              <Tooltip title={model.description}>
                <IconButton size="small">
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            {onEdit && (
              <IconButton size="small" onClick={handleEdit}>
                <EditIcon fontSize="small" />
              </IconButton>
            )}
            {onDelete && (
              <IconButton size="small" color="error" onClick={handleDelete}>
                <DeleteIcon fontSize="small" />
              </IconButton>
            )}
          </Stack>
        </Box>
        
        <Typography variant="body2" color="text.secondary" mb={1} noWrap>
          {model.name}
        </Typography>

        {provider && (
          <Box display="flex" alignItems="center" mb={1}>
            <StorageIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary', fontSize: '0.875rem' }} />
            <Typography variant="body2" color="text.secondary">
              {provider.name} ({provider.type})
            </Typography>
          </Box>
        )}

        <Box display="flex" alignItems="center" mb={1}>
          <HttpIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary', fontSize: '0.875rem' }} />
          <Typography variant="body2" color="text.secondary" noWrap>
            {truncatedEndpoint}
          </Typography>
        </Box>

        <Box display="flex" alignItems="center" mb={2}>
          <KeyIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary', fontSize: '0.875rem' }} />
          <Typography variant="body2" color="text.secondary">
            {hasApiKey ? '******' : '未設定'}
          </Typography>
        </Box>
        
        <Box display="flex" flexWrap="wrap" gap={1} mt={2}>
          <Chip 
            label={model.isActive ? 'アクティブ' : '非アクティブ'} 
            size="small"
            color={model.isActive ? 'success' : 'default'}
            variant="outlined"
          />
          
          {model.parameters && Object.keys(model.parameters).length > 0 && (
            <Tooltip title={
              <div>
                {Object.entries(model.parameters).map(([key, value]) => (
                  <div key={key}>{`${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`}</div>
                ))}
              </div>
            }>
              <Chip 
                label={`${Object.keys(model.parameters).length}個のパラメータ`}
                size="small"
                variant="outlined"
              />
            </Tooltip>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default ModelCard;
