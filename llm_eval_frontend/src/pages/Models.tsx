import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  CircularProgress,
  Button,
  Alert,
  TextField,
  InputAdornment,
  IconButton,
  Divider,
  Chip
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import { useModels, useProviders, useCreateModel, useUpdateModel, useDeleteModel } from '../hooks/useProviders';
import ModelCard from '../components/providers/ModelCard';
import ModelFormDialog from '../components/providers/ModelFormDialog';
import { useAppContext } from '../contexts/AppContext';
import { Model, ModelFormData } from '../types/provider';

/**
 * LLMモデル一覧ページ
 */
const Models: React.FC = () => {
  // 状態管理
  const [searchTerm, setSearchTerm] = useState('');
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [selectedProviderId, setSelectedProviderId] = useState<string>('');
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  const [providerFilter, setProviderFilter] = useState<string>('');

  // コンテキストから状態取得
  const { setError } = useAppContext();

  // モデルとプロバイダデータ取得
  const { data: models, isLoading, isError, error } = useModels();
  const { data: providers, isLoading: isLoadingProviders } = useProviders();

  // ミューテーションフック
  const createModel = useCreateModel(selectedProviderId);
  const updateModel = useUpdateModel(selectedProviderId, editingModel?.id || '');
  const deleteModel = useDeleteModel('');
  
  // エラーハンドリング
  if (error) {
    setError(`モデル一覧の取得に失敗しました: ${error.message}`);
  }
  
  // モデル追加ダイアログを開く
  const handleOpenFormDialog = (model?: Model) => {
    if (model) {
      setEditingModel(model);
      setSelectedProviderId(model.providerId);
    } else {
      setEditingModel(null);
      if (providers && providers.length > 0) {
        setSelectedProviderId(providers[0].id);
      }
    }
    setFormDialogOpen(true);
  };

  // モデル追加ダイアログを閉じる
  const handleCloseFormDialog = () => {
    setFormDialogOpen(false);
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
      handleCloseFormDialog();
    } catch (err) {
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

  // URLクエリパラメータからプロバイダIDを取得
  const { search } = window.location;
  const queryParams = new URLSearchParams(search);
  const queryProviderId = queryParams.get('providerId');

  // URLにproviderIdがある場合、プロバイダフィルタを設定
  React.useEffect(() => {
    if (queryProviderId) {
      setProviderFilter(queryProviderId);
    }
  }, [queryProviderId]);

  // プロバイダ選択ハンドラ
  const handleProviderFilterChange = (providerId: string) => {
    setProviderFilter(providerId === providerFilter ? '' : providerId);
  };

  // 検索条件とプロバイダでモデルをフィルタリング
  const filteredModels = models ? models.filter(model => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = (
      model.name.toLowerCase().includes(term) ||
      (model.displayName && model.displayName.toLowerCase().includes(term))
    );
    const matchesProvider = !providerFilter || model.providerId === providerFilter;
    return matchesSearch && matchesProvider;
  }) : [];
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          LLMモデル管理
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenFormDialog()}
          disabled={isLoadingProviders || !providers || providers.length === 0}
        >
          モデルを追加
        </Button>
      </Box>
      
      <Box mb={3}>
        <TextField
          fullWidth
          placeholder="モデル名で検索..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: searchTerm && (
              <InputAdornment position="end">
                <IconButton onClick={() => setSearchTerm('')} size="small">
                  <ClearIcon />
                </IconButton>
              </InputAdornment>
            )
          }}
          variant="outlined"
          size="small"
        />
      </Box>

      {/* プロバイダフィルタ */}
      {providers && providers.length > 0 && (
        <Box mb={3}>
          <Typography variant="subtitle2" gutterBottom>
            プロバイダでフィルタ:
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {providers.map((provider) => (
              <Chip
                key={provider.id}
                label={provider.name}
                variant={providerFilter === provider.id ? "filled" : "outlined"}
                color={providerFilter === provider.id ? "primary" : "default"}
                onClick={() => handleProviderFilterChange(provider.id)}
                clickable
              />
            ))}
            {providerFilter && (
              <Chip
                label="フィルタをクリア"
                variant="outlined"
                onClick={() => setProviderFilter('')}
                color="error"
                size="small"
              />
            )}
          </Box>
        </Box>
      )}
      
      <Divider sx={{ mb: 3 }} />
      
      {/* モデル一覧 */}
      {isLoading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : isError ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          モデル一覧の取得中にエラーが発生しました。
        </Alert>
      ) : filteredModels.length > 0 ? (
        <Grid container spacing={2}>
          {filteredModels.map((model) => (
            <Grid item xs={12} sm={6} md={4} key={model.id}>
              <ModelCard
                model={model}
                onSelect={() => {}}
                onEdit={handleOpenFormDialog}
                onDelete={handleDeleteModel}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Alert severity="info">
          {searchTerm ?
            '検索条件に一致するモデルが見つかりませんでした。' :
            'モデルが登録されていません。「モデルを追加」ボタンをクリックして新しいモデルを登録してください。'
          }
        </Alert>
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
        providerId={selectedProviderId}
      />
    </Box>
  );
};

export default Models;