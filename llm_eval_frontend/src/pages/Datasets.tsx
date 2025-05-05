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
import { useDatasets, useDeleteDataset, useUploadJsonFile } from '../hooks/useDatasets';
import { Dataset, DatasetUploadType } from '../types/dataset';
import { useAppContext } from '../contexts/AppContext';
import DatasetCard from '../components/datasets/DatasetCard';
import DatasetUploadDialog from '../components/datasets/DatasetUploadDialog';
import { useNavigate } from 'react-router-dom';

/**
 * データセット管理ページ
 */
const Datasets: React.FC = () => {
  const navigate = useNavigate();
  
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  
  // タブ状態
  const [tabValue, setTabValue] = useState<string | null>(null);
  
  // ダイアログの状態
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  
  // データセットデータの取得
  const { 
    data: datasets, 
    isLoading, 
    isError, 
    error 
  } = useDatasets(tabValue);
  
  // ミューテーションフック
  const deleteDataset = useDeleteDataset();
  const uploadJsonFile = useUploadJsonFile();
  
  // エラーハンドリング
  if (error) {
    setError(`データセットの取得に失敗しました: ${error.message}`);
  }
  
  // アップロードダイアログを開く
  const handleOpenUploadDialog = () => {
    setUploadDialogOpen(true);
  };
  
  // アップロードダイアログを閉じる
  const handleCloseUploadDialog = () => {
    setUploadDialogOpen(false);
  };
  
  // アップロードを実行
  const handleUploadDataset = async (file: File, type: DatasetUploadType) => {
    try {
      await uploadJsonFile.mutateAsync({ file, type });
    } catch (err) {
      if (err instanceof Error) {
        setError(`データセットのアップロードに失敗しました: ${err.message}`);
      }
      throw err;
    }
  };
  
  // データセットの削除を実行
  const handleDeleteDataset = async (filePath: string) => {
    try {
      await deleteDataset.mutateAsync(filePath);
    } catch (err) {
      if (err instanceof Error) {
        setError(`データセットの削除に失敗しました: ${err.message}`);
      }
    }
  };
  
  // データセットの詳細を表示
  const handleViewDataset = (dataset: Dataset) => {
    navigate(`/datasets/${dataset.name}`);
  };

  // タブ変更ハンドラ
  const handleTabChange = (event: React.SyntheticEvent, newValue: string | null) => {
    setTabValue(newValue);
  };
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          データセット管理
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenUploadDialog}
        >
          JSONファイルをアップロード
        </Button>
      </Box>
      
      <Tabs
        value={tabValue}
        onChange={handleTabChange}
        indicatorColor="primary"
        textColor="primary"
        sx={{ mb: 2 }}
      >
        <Tab label="すべて" value={null} />
        <Tab label="テスト用データセット" value="test" />
        <Tab label="n-shot用データセット" value="n_shot" />
      </Tabs>
      
      <Divider sx={{ mb: 3 }} />
      
      {isLoading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : isError ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          データセットの取得中にエラーが発生しました。
        </Alert>
      ) : datasets && datasets.length > 0 ? (
        <Grid container spacing={2}>
          {datasets.map((dataset) => (
            <Grid item xs={12} sm={6} md={4} key={dataset.file_path || dataset.name}>
              <DatasetCard
                dataset={dataset}
                onDelete={handleDeleteDataset}
                onView={handleViewDataset}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            データセットが登録されていません。「JSONファイルをアップロード」ボタンをクリックして最初のデータセットを登録してください。
          </Typography>
        </Paper>
      )}
      
      {/* データセットアップロードダイアログ */}
      <DatasetUploadDialog
        open={uploadDialogOpen}
        onClose={handleCloseUploadDialog}
        onUpload={handleUploadDataset}
        isUploading={uploadJsonFile.isPending}
      />
    </Box>
  );
};

export default Datasets;
