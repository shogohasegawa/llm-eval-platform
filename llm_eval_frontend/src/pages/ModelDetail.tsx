import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Grid, 
  Paper, 
  CircularProgress,
  Alert,
  Divider,
  Chip,
  List,
  ListItem,
  ListItemText
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { useModel, useProvider } from '../hooks/useProviders';
import OllamaModelDownloader from '../components/providers/OllamaModelDownloader';
import ModelFormDialog from '../components/providers/ModelFormDialog';
import { ModelFormData } from '../types/provider';
import { useAppContext } from '../contexts/AppContext';

/**
 * モデル詳細ページ
 */
const ModelDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const modelId = id || '';
  
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  
  // ダイアログの状態
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  
  // モデルデータの取得
  const { 
    data: model, 
    isLoading: isLoadingModel, 
    isError: isErrorModel,
    error: modelError
  } = useModel(modelId);
  
  // プロバイダ情報の取得（モデルが読み込まれた後）
  const {
    data: provider,
    isLoading: isLoadingProvider
  } = useProvider(model?.providerId || '', {
    enabled: !!model?.providerId
  });
  
  // エラーハンドリング
  if (modelError) {
    setError(`モデルの取得に失敗しました: ${modelError.message}`);
  }
  
  // ダイアログを開く
  const handleOpenFormDialog = () => {
    setFormDialogOpen(true);
  };
  
  // ダイアログを閉じる
  const handleCloseFormDialog = () => {
    setFormDialogOpen(false);
  };
  
  // モデルの編集を実行
  const handleSubmitModel = async (data: ModelFormData) => {
    // 実際の編集処理はここに追加
    console.log('Edit model data:', data);
    handleCloseFormDialog();
    
    // ページをリロードするかクエリを無効化して最新データを取得
    window.location.reload();
  };
  
  // モデル一覧に戻る
  const handleBackToModels = () => {
    navigate('/models');
  };
  
  // プロバイダ詳細ページに移動
  const handleGoToProvider = () => {
    if (model?.providerId) {
      navigate(`/providers/${model.providerId}`);
    }
  };
  
  // ローディング中
  if (isLoadingModel) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }
  
  // エラー発生時
  if (isErrorModel || !model) {
    return (
      <Box p={3}>
        <Alert severity="error" sx={{ mb: 3 }}>
          モデルの取得中にエラーが発生しました。
        </Alert>
        <Button variant="outlined" onClick={handleBackToModels}>
          モデル一覧に戻る
        </Button>
      </Box>
    );
  }
  
  // APIキーとエンドポイントの表示用に加工
  const displayApiKey = model.apiKey ? '********' : '未設定';
  const displayEndpoint = model.endpoint || '未設定';
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Button variant="outlined" onClick={handleBackToModels} sx={{ mb: 1 }}>
            モデル一覧に戻る
          </Button>
          <Typography variant="h4" component="h1">
            {model.displayName || model.name}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {model.name}
          </Typography>
        </Box>
        <Box>
          <Button
            variant="contained"
            color="primary"
            onClick={handleOpenFormDialog}
            sx={{ mr: 1 }}
          >
            編集
          </Button>
          <Button
            variant="outlined"
            onClick={handleGoToProvider}
          >
            プロバイダ詳細
          </Button>
        </Box>
      </Box>
      
      <Divider sx={{ mb: 3 }} />
      
      <Grid container spacing={3}>
        {/* 基本情報 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              基本情報
            </Typography>
            <List dense>
              <ListItem>
                <ListItemText 
                  primary="モデルID" 
                  secondary={model.id} 
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="モデル名" 
                  secondary={model.name} 
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="表示名" 
                  secondary={model.displayName || model.name} 
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="説明" 
                  secondary={model.description || '説明なし'} 
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="状態" 
                  secondary={
                    <Chip 
                      label={model.isActive ? 'アクティブ' : '非アクティブ'} 
                      color={model.isActive ? 'success' : 'default'} 
                      size="small"
                    />
                  } 
                />
              </ListItem>
            </List>
          </Paper>
        </Grid>
        
        {/* 接続情報 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              接続情報
            </Typography>
            <List dense>
              <ListItem>
                <ListItemText 
                  primary="プロバイダ" 
                  secondary={
                    isLoadingProvider ? (
                      <CircularProgress size={20} />
                    ) : provider ? (
                      `${provider.name} (${provider.type})`
                    ) : '不明'
                  } 
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="エンドポイント" 
                  secondary={displayEndpoint} 
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="APIキー" 
                  secondary={displayApiKey} 
                />
              </ListItem>
            </List>
          </Paper>
        </Grid>
        
        {/* パラメータ */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              モデルパラメータ
            </Typography>
            {model.parameters && Object.keys(model.parameters).length > 0 ? (
              <List dense>
                {Object.entries(model.parameters).map(([key, value]) => (
                  <ListItem key={key}>
                    <ListItemText 
                      primary={key} 
                      secondary={
                        typeof value === 'object' 
                          ? JSON.stringify(value) 
                          : String(value)
                      } 
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary">
                設定されているパラメータはありません
              </Typography>
            )}
          </Paper>
        </Grid>
        
        {/* Ollamaプロバイダの場合にダウンロードボタンを表示 */}
        {provider && provider.type === 'ollama' && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Ollamaモデル管理
              </Typography>
              <Box
                onClick={(e) => {
                  e.stopPropagation();
                }}
                sx={{ mt: 2 }}
              >
                <OllamaModelDownloader 
                  modelId={model.id}
                  modelName={model.name}
                  endpoint={model.endpoint || provider.endpoint}
                />
              </Box>
            </Paper>
          </Grid>
        )}
      </Grid>
      
      {/* モデル編集ダイアログ */}
      <ModelFormDialog
        open={formDialogOpen}
        onClose={handleCloseFormDialog}
        onSubmit={handleSubmitModel}
        initialData={{
          name: model.name,
          displayName: model.displayName || '',
          description: model.description || '',
          endpoint: model.endpoint || '',
          apiKey: model.apiKey || '',
          parameters: model.parameters || {},
          isActive: model.isActive,
          providerId: model.providerId
        }}
        isSubmitting={false}
        providerId={model.providerId}
      />
    </Box>
  );
};

export default ModelDetail;