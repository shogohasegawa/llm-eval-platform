import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Grid,
  Paper,
  CircularProgress,
  Alert,
  Divider
} from '@mui/material';
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
  
  // モデル一覧に移動するハンドラ
  const handleGoToModels = () => {
    navigate(`/models?providerId=${providerId}`);
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
          variant="outlined"
          onClick={handleGoToModels}
        >
          モデル一覧を表示
        </Button>
      </Box>
      
      <Divider sx={{ mb: 3 }} />

      {/* 関連モデル情報 */}
      <Box mb={3}>
        <Typography variant="subtitle1" gutterBottom>
          このプロバイダに関連するモデルは「モデル一覧」で確認・管理できます。
        </Typography>
        <Button
          variant="outlined"
          onClick={handleGoToModels}
          sx={{ mt: 1 }}
        >
          モデル一覧を表示
        </Button>
      </Box>

      {/* プロバイダ設定 */}
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
