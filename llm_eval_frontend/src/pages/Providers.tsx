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
  Tab,
  Tabs
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { useNavigate } from 'react-router-dom';
import ProviderCard from '../components/providers/ProviderCard';
import ProviderFormDialog from '../components/providers/ProviderFormDialog';
import ModelCard from '../components/providers/ModelCard';
import ModelFormDialog from '../components/providers/ModelFormDialog';
import { 
  useProviders, 
  useCreateProvider, 
  useUpdateProvider,
  useDeleteProvider,
  useModels, 
  useCreateModel, 
  useUpdateModel, 
  useDeleteModel 
} from '../hooks/useProviders';
import { Provider, ProviderFormData, Model, ModelFormData } from '../types/provider';
import { useAppContext } from '../contexts/AppContext';

/**
 * プロバイダおよびモデル管理ページ
 */
const Providers: React.FC = () => {
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  const navigate = useNavigate();
  
  // タブの状態
  const [tabValue, setTabValue] = useState(0);

  // プロバイダダイアログの状態
  const [providerDialogOpen, setProviderDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  
  // モデルダイアログの状態
  const [modelDialogOpen, setModelDialogOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  
  // プロバイダデータの取得
  const { 
    data: providers, 
    isLoading: isLoadingProviders, 
    isError: isErrorProviders, 
    error: providersError 
  } = useProviders();
  
  // モデルデータの取得
  const { 
    data: models, 
    isLoading: isLoadingModels, 
    isError: isErrorModels, 
    error: modelsError 
  } = useModels();
  
  // ミューテーションフック（プロバイダ）
  const createProvider = useCreateProvider();
  const updateProvider = useUpdateProvider(editingProvider?.id || '');
  const deleteProvider = useDeleteProvider();
  
  // ミューテーションフック（モデル）
  const createModel = useCreateModel();
  const updateModel = useUpdateModel(editingModel?.id || '');
  const deleteModel = useDeleteModel();
  
  // エラーハンドリング
  if (providersError) {
    setError(`プロバイダの取得に失敗しました: ${providersError.message}`);
  }
  
  if (modelsError) {
    setError(`モデルの取得に失敗しました: ${modelsError.message}`);
  }
  
  // タブの変更ハンドラ
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };
  
  // プロバイダの追加/編集ダイアログを開く
  const handleOpenProviderDialog = (provider?: Provider) => {
    if (provider) {
      setEditingProvider(provider);
    } else {
      setEditingProvider(null);
    }
    setProviderDialogOpen(true);
  };
  
  // プロバイダの追加/編集ダイアログを閉じる
  const handleCloseProviderDialog = () => {
    setProviderDialogOpen(false);
    setEditingProvider(null);
  };
  
  // プロバイダの追加/編集を実行
  const handleSubmitProvider = async (data: ProviderFormData) => {
    try {
      if (editingProvider) {
        await updateProvider.mutateAsync(data);
      } else {
        await createProvider.mutateAsync(data);
      }
      handleCloseProviderDialog();
    } catch (err) {
      if (err instanceof Error) {
        setError(`プロバイダの${editingProvider ? '更新' : '追加'}に失敗しました: ${err.message}`);
      }
    }
  };
  
  // プロバイダの削除を実行
  const handleDeleteProvider = async (providerId: string) => {
    try {
      await deleteProvider.mutateAsync(providerId);
    } catch (err) {
      if (err instanceof Error) {
        setError(`プロバイダの削除に失敗しました: ${err.message}`);
      }
    }
  };
  
  // プロバイダ詳細ページに遷移
  const handleSelectProvider = (provider: Provider) => {
    navigate(`/providers/${provider.id}`);
  };
  
  // モデルの追加/編集ダイアログを開く
  const handleOpenModelDialog = (model?: Model) => {
    if (model) {
      setEditingModel(model);
    } else {
      setEditingModel(null);
    }
    setModelDialogOpen(true);
  };
  
  // モデルの追加/編集ダイアログを閉じる
  const handleCloseModelDialog = () => {
    setModelDialogOpen(false);
    setEditingModel(null);
  };
  
  // モデルの追加/編集を実行
  const handleSubmitModel = async (data: ModelFormData) => {
    try {
      if (editingModel) {
        await updateModel.mutateAsync(data);
      } else {
        await createModel.mutateAsync(data);
      }
      handleCloseModelDialog();
    } catch (err) {
      if (err instanceof Error) {
        setError(`モデルの${editingModel ? '更新' : '追加'}に失敗しました: ${err.message}`);
      }
    }
  };
  
  // モデルの削除を実行
  const handleDeleteModel = async (model: Model) => {
    try {
      await deleteModel.mutateAsync({
        modelId: model.id,
        providerId: model.providerId
      });
    } catch (err) {
      if (err instanceof Error) {
        setError(`モデルの削除に失敗しました: ${err.message}`);
      }
    }
  };
  
  // モデル詳細ページに遷移
  const handleSelectModel = (model: Model) => {
    // モデル詳細ページへの遷移
    navigate(`/models/${model.id}`);
  };
  
  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="LLM management tabs">
          <Tab label="プロバイダ" id="tab-0" />
          <Tab label="モデル" id="tab-1" />
        </Tabs>
      </Box>
      
      {/* プロバイダタブ */}
      {tabValue === 0 && (
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Typography variant="h4" component="h1">
              LLMプロバイダ管理
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenProviderDialog()}
            >
              プロバイダを追加
            </Button>
          </Box>
          
          <Divider sx={{ mb: 3 }} />
          
          {isLoadingProviders ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : isErrorProviders ? (
            <Alert severity="error" sx={{ mb: 3 }}>
              プロバイダの取得中にエラーが発生しました。
            </Alert>
          ) : providers && providers.length > 0 ? (
            <Grid container spacing={2}>
              {providers.map((provider) => (
                <Grid item xs={12} sm={6} md={4} key={provider.id}>
                  <ProviderCard
                    provider={{
                      ...provider,
                      // プロバイダごとのモデル数を取得
                      modelCount: models?.filter(m => m.providerId === provider.id).length || 0
                    }}
                    onEdit={handleOpenProviderDialog}
                    onDelete={() => handleDeleteProvider(provider.id)}
                    onSelect={handleSelectProvider}
                  />
                </Grid>
              ))}
            </Grid>
          ) : (
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                プロバイダが登録されていません。「プロバイダを追加」ボタンをクリックして最初のプロバイダを登録してください。
              </Typography>
            </Paper>
          )}
          
          {/* プロバイダ追加/編集ダイアログ */}
          <ProviderFormDialog
            open={providerDialogOpen}
            onClose={handleCloseProviderDialog}
            onSubmit={handleSubmitProvider}
            initialData={editingProvider ? {
              name: editingProvider.name,
              type: editingProvider.type,
              endpoint: editingProvider.endpoint,
              apiKey: editingProvider.apiKey,
              isActive: editingProvider.isActive
            } : undefined}
            isSubmitting={createProvider.isPending || updateProvider.isPending}
          />
        </>
      )}
      
      {/* モデルタブ */}
      {tabValue === 1 && (
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Typography variant="h4" component="h1">
              LLMモデル管理
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenModelDialog()}
            >
              モデルを追加
            </Button>
          </Box>
          
          <Divider sx={{ mb: 3 }} />
          
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
                    onEdit={handleOpenModelDialog}
                    onDelete={() => handleDeleteModel(model)}
                    onSelect={handleSelectModel}
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
          
          {/* モデル追加/編集ダイアログ */}
          <ModelFormDialog
            open={modelDialogOpen}
            onClose={handleCloseModelDialog}
            onSubmit={handleSubmitModel}
            initialData={editingModel ? {
              providerId: editingModel.providerId,
              name: editingModel.name,
              displayName: editingModel.displayName,
              description: editingModel.description,
              endpoint: editingModel.endpoint || '',
              apiKey: editingModel.apiKey || '',
              parameters: editingModel.parameters,
              isActive: editingModel.isActive
            } : undefined}
            isSubmitting={createModel.isPending || updateModel.isPending}
          />
        </>
      )}
    </Box>
  );
};

export default Providers;
