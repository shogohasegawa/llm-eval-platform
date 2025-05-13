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
import AddIcon from '@mui/icons-material/Add';
import { useNavigate } from 'react-router-dom';
import ProviderCard from '../components/providers/ProviderCard';
import ProviderFormDialog from '../components/providers/ProviderFormDialog';
import {
  useProviders,
  useCreateProvider,
  useUpdateProvider,
  useDeleteProvider
} from '../hooks/useProviders';
import { Provider, ProviderFormData } from '../types/provider';
import { useAppContext } from '../contexts/AppContext';

/**
 * プロバイダ管理ページ
 */
const Providers: React.FC = () => {
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  const navigate = useNavigate();
  
  // プロバイダダイアログの状態
  const [providerDialogOpen, setProviderDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  
  // プロバイダデータの取得
  const {
    data: providers,
    isLoading: isLoadingProviders,
    isError: isErrorProviders,
    error: providersError
  } = useProviders();

  // ミューテーションフック（プロバイダ）
  const createProvider = useCreateProvider();
  const updateProvider = useUpdateProvider(editingProvider?.id || '');
  const deleteProvider = useDeleteProvider();
  
  // データ取得状況のログ
  console.log('Providers data:', providers);
  console.log('Provider loading:', isLoadingProviders);
  console.log('Provider error:', isErrorProviders);
  
  // エラーハンドリング
  if (providersError) {
    console.error('Provider error details:', providersError);
    setError(`プロバイダの取得に失敗しました: ${providersError.message}`);
  }
  
  // プロバイダの追加/編集ダイアログを開く
  const handleOpenProviderDialog = (provider?: Provider) => {
    console.log('Opening provider dialog with:', provider);
    // 編集か新規作成かに関わらず、まずステートを更新
    setEditingProvider(provider || null);
    // 次にダイアログを開く
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
  
  return (
    <Box sx={{ p: 3 }}>
      {/* プロバイダ管理 */}
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
                    provider={provider}
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
    </Box>
  );
};

export default Providers;
