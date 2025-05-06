import React, { useState } from 'react';
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
  Button,
  Divider
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import InfoIcon from '@mui/icons-material/Info';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import StorageIcon from '@mui/icons-material/Storage';
import HttpIcon from '@mui/icons-material/Http';
import KeyIcon from '@mui/icons-material/Key';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import { Model } from '../../types/provider';
import { useProvider } from '../../hooks/useProviders';
import OllamaModelDownloader from './OllamaModelDownloader';

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
  // フィールド名の正規化（スネークケース・キャメルケース対応）
  const normalizedModel = {
    ...model,
    // キャメルケースとスネークケースの両方に対応
    id: model.id || model.model_id || '',
    providerId: model.providerId || model.provider_id || '',
    displayName: model.displayName || model.display_name || model.name || '',
    isActive: model.isActive ?? model.is_active ?? true,
    apiKey: model.apiKey || model.api_key || '',
    endpoint: model.endpoint || ''
  };
  
  // プロバイダ情報を取得
  const { data: provider } = useProvider(normalizedModel.providerId);

  console.log('Rendering model card for:', normalizedModel);

  // useNavigate フックを使用
  const navigate = useNavigate();
  
  const handleClick = () => {
    // モデル詳細ページに遷移
    navigate(`/models/${normalizedModel.id}`);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit) {
      onEdit(normalizedModel);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete && confirm('このモデルを削除してもよろしいですか？')) {
      onDelete(normalizedModel);
    }
  };

  // エンドポイントとAPIキーの表示用に加工
  const truncatedEndpoint = normalizedModel.endpoint ? 
    normalizedModel.endpoint.length > 30 ? 
      normalizedModel.endpoint.substring(0, 27) + '...' : 
      normalizedModel.endpoint : 
    '未設定';
  
  const hasApiKey = normalizedModel.apiKey && normalizedModel.apiKey.length > 0;

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
            {normalizedModel.displayName}
          </Typography>
          <Stack direction="row" spacing={1}>
            {normalizedModel.description && (
              <Tooltip title={normalizedModel.description}>
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
          {normalizedModel.name}
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
            label={normalizedModel.isActive ? 'アクティブ' : '非アクティブ'} 
            size="small"
            color={normalizedModel.isActive ? 'success' : 'default'}
            variant="outlined"
          />
          
          {/* デバッグ情報（開発中のみ表示） */}
          {import.meta.env.DEV && (
            <Tooltip title="モデルID">
              <Chip 
                label={`ID: ${normalizedModel.id.substring(0, 8)}...`}
                size="small"
                variant="outlined"
                color="info"
              />
            </Tooltip>
          )}
          
          {normalizedModel.parameters && Object.keys(normalizedModel.parameters).length > 0 && (
            <Tooltip title={
              <div>
                {Object.entries(normalizedModel.parameters).map(([key, value]) => (
                  <div key={key}>{`${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`}</div>
                ))}
              </div>
            }>
              <Chip 
                label={`${Object.keys(normalizedModel.parameters).length}個のパラメータ`}
                size="small"
                variant="outlined"
              />
            </Tooltip>
          )}
        </Box>
        
        {/* Ollamaプロバイダの場合にダウンロードボタンを表示 */}
        {provider && provider.type === 'ollama' && (
          <>
            <Divider sx={{ my: 2 }} />
            <Box 
              display="flex" 
              justifyContent="center" 
              onClick={(e) => {
                e.stopPropagation();  // カード全体のクリックイベントへの伝播を防止
              }}
            >
              <OllamaModelDownloader 
                modelId={normalizedModel.id}
                modelName={normalizedModel.name}
                endpoint={normalizedModel.endpoint || provider.endpoint}
              />
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default ModelCard;
