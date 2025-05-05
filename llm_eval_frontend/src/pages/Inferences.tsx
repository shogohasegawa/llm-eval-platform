import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Grid, 
  Paper, 
  CircularProgress,
  Alert,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { useInferences, useCreateInference, useDeleteInference, useRunInference, useStopInference } from '../hooks/useInferences';
import { useDatasets } from '../hooks/useDatasets';
import { useProviders, useModels } from '../hooks/useProviders';
import { Inference, InferenceFormData, InferenceFilterOptions } from '../types/inference';
import { useAppContext } from '../contexts/AppContext';
import InferenceCard from '../components/inferences/InferenceCard';
import InferenceFormDialog from '../components/inferences/InferenceFormDialog';
import { useNavigate } from 'react-router-dom';

/**
 * 推論管理ページ
 */
const Inferences: React.FC = () => {
  const navigate = useNavigate();
  
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  
  // フィルター状態
  const [filters, setFilters] = useState<InferenceFilterOptions>({});
  
  // ダイアログの状態
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  
  // 推論データの取得
  const { 
    data: inferences, 
    isLoading: isLoadingInferences, 
    isError: isErrorInferences, 
    error: inferencesError 
  } = useInferences(filters);
  
  // データセットデータの取得
  const {
    data: datasets,
    isLoading: isLoadingDatasets,
    isError: isErrorDatasets,
    error: datasetsError
  } = useDatasets();
  
  // プロバイダデータの取得
  const {
    data: providers,
    isLoading: isLoadingProviders,
    isError: isErrorProviders,
    error: providersError
  } = useProviders();
  
  // モデルデータの取得
  const {
    data: modelsData,
    isLoading: isLoadingModels,
    isError: isErrorModels,
    error: modelsError
  } = useModels();
  
  // ミューテーションフック
  const createInference = useCreateInference();
  const deleteInference = useDeleteInference();
  const runInference = useRunInference('');
  const stopInference = useStopInference('');
  
  // モデルリストの取得と整形
  const [models, setModels] = useState<any[]>([]);
  
  // プロバイダとモデルを連携
  useEffect(() => {
    if (providers && modelsData) {
      console.log('Providers:', providers);
      console.log('Models:', modelsData);
      
      // 各モデルにproviderId情報が既に含まれていることを確認
      const processedModels = modelsData.map(model => {
        // 対応するプロバイダ情報を取得
        const provider = providers.find(p => p.id === model.providerId);
        return {
          ...model,
          providerName: provider?.name || 'Unknown',
          providerType: provider?.type || 'unknown'
        };
      });
      
      setModels(processedModels);
      console.log('Processed models:', processedModels);
    }
  }, [providers, modelsData]);
  
  // エラーハンドリング
  if (inferencesError) {
    setError(`推論の取得に失敗しました: ${inferencesError.message}`);
  }
  
  if (datasetsError) {
    setError(`データセットの取得に失敗しました: ${datasetsError.message}`);
  }
  
  if (providersError) {
    setError(`プロバイダの取得に失敗しました: ${providersError.message}`);
  }
  
  if (modelsError) {
    setError(`モデルの取得に失敗しました: ${modelsError.message}`);
  }
  
  // 推論の作成ダイアログを開く
  const handleOpenFormDialog = () => {
    setFormDialogOpen(true);
  };
  
  // 推論の作成ダイアログを閉じる
  const handleCloseFormDialog = () => {
    setFormDialogOpen(false);
  };
  
  // 推論の作成を実行
  const handleSubmitInference = async (data: InferenceFormData) => {
    try {
      console.log('Submitting inference data:', data);
      await createInference.mutateAsync(data);
      handleCloseFormDialog();
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の作成に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 推論の削除を実行
  const handleDeleteInference = async (id: string) => {
    try {
      await deleteInference.mutateAsync(id);
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の削除に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 推論の実行を開始
  const handleRunInference = async (inference: Inference) => {
    try {
      await runInference.mutateAsync(inference.id);
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の実行に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 推論の実行を停止
  const handleStopInference = async (inference: Inference) => {
    try {
      await stopInference.mutateAsync(inference.id);
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の停止に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 推論の詳細を表示
  const handleViewInference = (inference: Inference) => {
    navigate(`/inferences/${inference.id}`);
  };
  
  // フィルターの変更処理
  const handleFilterChange = (e: SelectChangeEvent<string | number>) => {
    const { name, value } = e.target;
    if (name) {
      setFilters(prev => ({
        ...prev,
        [name]: value === 'all' ? undefined : value
      }));
    }
  };
  
  // ローディング中
  const isLoading = isLoadingInferences || isLoadingDatasets || isLoadingProviders || isLoadingModels;
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          推論管理
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenFormDialog}
          disabled={!datasets?.length || !providers?.length || !models?.length}
        >
          推論を作成
        </Button>
      </Box>
      
      <Divider sx={{ mb: 3 }} />
      
      {/* フィルター */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>データセット</InputLabel>
              <Select
                name="datasetId"
                value={filters.datasetId || 'all'}
                onChange={handleFilterChange}
                label="データセット"
              >
                <MenuItem value="all">すべて</MenuItem>
                {datasets?.map((dataset) => (
                  <MenuItem key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>プロバイダ</InputLabel>
              <Select
                name="providerId"
                value={filters.providerId || 'all'}
                onChange={handleFilterChange}
                label="プロバイダ"
              >
                <MenuItem value="all">すべて</MenuItem>
                {providers?.map((provider) => (
                  <MenuItem key={provider.id} value={provider.id}>
                    {provider.name} ({provider.type || 'unknown'})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>ステータス</InputLabel>
              <Select
                name="status"
                value={filters.status || 'all'}
                onChange={handleFilterChange}
                label="ステータス"
              >
                <MenuItem value="all">すべて</MenuItem>
                <MenuItem value="pending">待機中</MenuItem>
                <MenuItem value="running">実行中</MenuItem>
                <MenuItem value="completed">完了</MenuItem>
                <MenuItem value="failed">失敗</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>
      
      {isLoading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : isErrorInferences ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          推論の取得中にエラーが発生しました。
        </Alert>
      ) : inferences && inferences.length > 0 ? (
        <Grid container spacing={2}>
          {inferences.map((inference) => (
            <Grid item xs={12} sm={6} md={4} key={inference.id}>
              <InferenceCard
                inference={inference}
                onRun={handleRunInference}
                onStop={handleStopInference}
                onDelete={handleDeleteInference}
                onView={handleViewInference}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            推論が登録されていません。「推論を作成」ボタンをクリックして最初の推論を作成してください。
          </Typography>
        </Paper>
      )}
      
      {/* 推論作成ダイアログ */}
      {formDialogOpen && datasets && providers && (
        <InferenceFormDialog
          open={formDialogOpen}
          onClose={handleCloseFormDialog}
          onSubmit={handleSubmitInference}
          isSubmitting={createInference.isPending}
          datasets={datasets}
          providers={providers}
          models={models}
        />
      )}
    </Box>
  );
};

export default Inferences;
