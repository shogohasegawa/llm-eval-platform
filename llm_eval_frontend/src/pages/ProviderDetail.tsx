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
  Tabs,
  Tab
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { useParams, useNavigate } from 'react-router-dom';
import { useProvider, useProviderModels, useCreateModel, useUpdateModel, useDeleteModel } from '../hooks/useProviders';
import { Model, ModelFormData } from '../types/provider';
import { useAppContext } from '../contexts/AppContext';
import ModelCard from '../components/providers/ModelCard';
import ModelFormDialog from '../components/providers/ModelFormDialog';

/**
 * プロバイダ詳細ページ
 */
const ProviderDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const providerId = id || '';
  
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  
  // タブの状態
  const [tabValue, setTabValue] = useState(0);
  
  // ダイアログの状態
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  
  // プロバイダとモデルデータの取得
  const { 
    data: provider, 
    isLoading: isLoadingProvider, 
    isError: isErrorProvider,
    error: providerError
  } = useProvider(providerId);
  
  const {
    data: models,
    isLoading: isLoadingModels,
    isError: isErrorModels,
    error: modelsError
  } = useProviderModels(providerId);
  
  // ミューテーションフック
  const createModel = useCreateModel(providerId);
  const updateModel = useUpdateModel(providerId, editingModel?.id || '');
  const deleteModel = useDeleteModel(providerId);
  
  // エラーハンドリング
  if (providerError) {
    setError(`プロバイダの取得に失敗しました: ${providerError.message}`);
  }
  
  if (modelsError) {
    setError(`モデルの取得に失敗しました: ${modelsError.message}`);
  }
  
  // タブの変更ハンドラ
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };
  
  // モデルの追加/編集ダイアログを開く
  const handleOpenFormDialog = (model?: Model) => {
    if (model) {
      setEditingModel(model);
    } else {
      setEditingModel(null);
    }
    setFormDialogOpen(true);
  };
  
  // モデルの追加/編集ダイアログを閉じる
  const handleCloseFormDialog = () => {
    setFormDialogOpen(false);
    setEditingModel(null);
  };
  
  // モデルの追加/編集を実行
  const handleSubmitModel = async (data: ModelFormData) => {
    try {
      console.log('Submitting model data:', data);
      if (editingModel) {
        const result = await updateModel.mutateAsync(data);
        console.log('Updated model:', result);
      } else {
        const result = await createModel.mutateAsync(data);
        console.log('Created model:', result);
      }
      handleCloseFormDialog();
    } catch (err) {
      console.error('Error submitting model:', err);
      if (err instanceof Error) {
        setError(`モデルの${editingModel ? '更新' : '追加'}に失敗しました: ${err.message}`);
      }
    }
  };
  
  // モデルの削除を実行
  const handleDeleteModel = async (model: Model) => {
    try {
      await deleteModel.mutateAsync(model.id);
    } catch (err) {
      if (err instanceof Error) {
        setError(`モデルの削除に失敗しました: ${err.message}`);
      }
    }
  };
  
  // モデルを選択
  const handleSelectModel = (model: Model) => {
    // モデル選択時の処理（詳細表示など）
    console.log('Selected model:', model);
  };
  
  // プロバイダ一覧に戻る
  const handleBackToProviders = () => {
    navigate('/providers');
  };
  
  // ローディング中
  if (isLoadingProvider) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }
  
  // エラー発生時
  if (isErrorProvider || !provider) {
    return (
      <Box p={3}>
        <Alert severity="error" sx={{ mb: 3 }}>
          プロバイダの取得中にエラーが発生しました。
        </Alert>
        <Button variant="outlined" onClick={handleBackToProviders}>
          プロバイダ一覧に戻る
        </Button>
      </Box>
    );
  }
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Button variant="outlined" onClick={handleBackToProviders} sx={{ mb: 1 }}>
            プロバイダ一覧に戻る
          </Button>
          <Typography variant="h4" component="h1">
            {provider.name}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            タイプ: {provider.type}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenFormDialog()}
        >
          モデルを追加
        </Button>
      </Box>
      
      <Divider sx={{ mb: 3 }} />
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="provider tabs">
          <Tab label="モデル" id="tab-0" />
          <Tab label="設定" id="tab-1" />
        </Tabs>
      </Box>
      
      {/* モデルタブ */}
      {tabValue === 0 && (
        <>
          {isLoadingModels ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : isErrorModels ? (
            <Alert severity="error" sx={{ mb: 3 }}>
              モデルの取得中にエラーが発生しました。
            </Alert>
          ) : models && models.length > 0 ? (
            <Grid container spacing={2}>
              {models.map((model) => (
                <Grid item xs={12} sm={6} md={4} key={model.id}>
                  <ModelCard
                    model={model}
                    onSelect={handleSelectModel}
                    onEdit={handleOpenFormDialog}
                    onDelete={handleDeleteModel}
                  />
                </Grid>
              ))}
            </Grid>
          ) : (
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                モデルが登録されていません。「モデルを追加」ボタンをクリックして最初のモデルを登録してください。
              </Typography>
            </Paper>
          )}
        </>
      )}
      
      {/* 設定タブ */}
      {tabValue === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            プロバイダ設定
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2">エンドポイント</Typography>
              <Typography variant="body1">{provider.endpoint || '設定なし'}</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2">APIキー</Typography>
              <Typography variant="body1">{provider.apiKey ? '********' : '設定なし'}</Typography>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="subtitle2">ステータス</Typography>
              <Typography variant="body1">{provider.isActive ? 'アクティブ' : '非アクティブ'}</Typography>
            </Grid>
          </Grid>
        </Paper>
      )}
      
      
      {/* モデル追加/編集ダイアログ */}
      <ModelFormDialog
        open={formDialogOpen}
        onClose={handleCloseFormDialog}
        onSubmit={handleSubmitModel}
        initialData={editingModel ? {
          name: editingModel.name,
          displayName: editingModel.displayName,
          description: editingModel.description,
          parameters: editingModel.parameters,
          isActive: editingModel.isActive
        } : undefined}
        isSubmitting={createModel.isPending || updateModel.isPending}
        providerId={providerId}
      />
    </Box>
  );
};

export default ProviderDetail;
