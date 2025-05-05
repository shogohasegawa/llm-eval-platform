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
  // キャメルケースとスネークケースの両方に対応するために正規化
  const normalizedProvider = {
    ...provider,
    // フィールドの正規化
    id: provider.id || '',
    isActive: provider.isActive ?? provider.is_active ?? true,
    // APIレスポンスの型の違いに対応
    modelCount: provider.modelCount !== undefined ? provider.modelCount : 
                (provider.models?.length || 0)
  };
  
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
      case 'anthropic':
        return '#0A46E4';
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
        borderColor: normalizedProvider.isActive ? 'primary.main' : 'divider',
        boxShadow: normalizedProvider.isActive ? 3 : 1
      }}
    >
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6" component="div">
            {normalizedProvider.name}
          </Typography>
          <Stack direction="row" spacing={1}>
            <IconButton size="small" onClick={() => onEdit(provider)} aria-label="編集">
              <EditIcon fontSize="small" />
            </IconButton>
            <IconButton 
              size="small" 
              onClick={() => onDelete(normalizedProvider.id)} 
              aria-label="削除"
              color="error"
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Box>
        
        <Box display="flex" alignItems="center" mb={2}>
          <Chip 
            label={normalizedProvider.type} 
            size="small" 
            sx={{ 
              backgroundColor: getProviderTypeColor(normalizedProvider.type),
              color: 'white',
              mr: 1
            }} 
          />
          <Chip 
            label={normalizedProvider.isActive ? 'アクティブ' : '非アクティブ'} 
            size="small"
            color={normalizedProvider.isActive ? 'success' : 'default'}
            variant="outlined"
          />
          
          {/* 開発環境でのみ表示するIDチップ */}
          {import.meta.env.DEV && (
            <Chip 
              label={`ID: ${normalizedProvider.id.substring(0, 6)}...`} 
              size="small"
              variant="outlined"
              color="info"
              sx={{ ml: 1 }}
            />
          )}
        </Box>
        
        <Typography variant="body2" color="text.secondary" mb={1}>
          モデル数: {normalizedProvider.modelCount}
        </Typography>
        
        {normalizedProvider.endpoint && (
          <Typography variant="body2" color="text.secondary" mb={1} noWrap>
            エンドポイント: {normalizedProvider.endpoint}
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
