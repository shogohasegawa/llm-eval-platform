import React from 'react';
import { Box, Card, CardContent, Typography, Button, Chip, Stack, IconButton } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { Provider } from '../../types/provider';

interface ProviderCardProps {
  provider: Provider;
  onEdit: (provider: Provider) => void;
  onDelete: (providerId: string) => void;
  onSelect: (provider: Provider) => void;
}

/**
 * プロバイダ情報を表示するカードコンポーネント
 */
const ProviderCard: React.FC<ProviderCardProps> = ({ provider, onEdit, onDelete, onSelect }) => {
  // プロバイダタイプに応じた色を設定
  const getProviderTypeColor = (type: string) => {
    switch (type) {
      case 'azure':
        return '#0078D4';
      case 'ollama':
        return '#FF6B6B';
      case 'openai':
        return '#10A37F';
      case 'huggingface':
        return '#FFBD59';
      case 'custom':
        return '#9C27B0';
      default:
        return '#757575';
    }
  };

  return (
    <Card 
      sx={{ 
        mb: 2, 
        border: '1px solid',
        borderColor: provider.isActive ? 'primary.main' : 'divider',
        boxShadow: provider.isActive ? 3 : 1
      }}
    >
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6" component="div">
            {provider.name}
          </Typography>
          <Stack direction="row" spacing={1}>
            <IconButton size="small" onClick={() => onEdit(provider)} aria-label="編集">
              <EditIcon fontSize="small" />
            </IconButton>
            <IconButton 
              size="small" 
              onClick={() => onDelete(provider.id)} 
              aria-label="削除"
              color="error"
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Box>
        
        <Box display="flex" alignItems="center" mb={2}>
          <Chip 
            label={provider.type} 
            size="small" 
            sx={{ 
              backgroundColor: getProviderTypeColor(provider.type),
              color: 'white',
              mr: 1
            }} 
          />
          <Chip 
            label={provider.isActive ? 'アクティブ' : '非アクティブ'} 
            size="small"
            color={provider.isActive ? 'success' : 'default'}
            variant="outlined"
          />
        </Box>
        
        <Typography variant="body2" color="text.secondary" mb={1}>
          モデル数: {provider.modelCount !== undefined ? provider.modelCount : provider.models?.length || 0}
        </Typography>
        
        {provider.endpoint && (
          <Typography variant="body2" color="text.secondary" mb={1} noWrap>
            エンドポイント: {provider.endpoint}
          </Typography>
        )}
        
        <Box mt={2} display="flex" justifyContent="flex-end">
          <Button 
            variant="contained" 
            size="small" 
            onClick={() => onSelect(provider)}
          >
            選択
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ProviderCard;
