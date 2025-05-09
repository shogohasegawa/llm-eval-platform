import React, { useState, useEffect } from 'react';
import { 
  Button, 
  CircularProgress, 
  Dialog, 
  DialogActions, 
  DialogContent, 
  DialogTitle, 
  TextField,
  Box,
  Typography,
  LinearProgress,
  Alert,
  Paper,
  Stack,
  Divider,
  Tooltip,
  IconButton 
} from '@mui/material';
import { OllamaModelDownload, OllamaDownloadStatus } from '../../types/ollama';
import { ollamaApi } from '../../api/ollama';
import RefreshIcon from '@mui/icons-material/Refresh';
import FileDownloadDoneIcon from '@mui/icons-material/FileDownloadDone';
import ErrorIcon from '@mui/icons-material/Error';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';

interface OllamaModelDownloaderProps {
  modelId: string;
  modelName: string;
  endpoint?: string;
  onDownloadComplete?: () => void;
  onClose?: () => void;
}

/**
 * Ollamaモデルのダウンロード管理コンポーネント
 */
const OllamaModelDownloader: React.FC<OllamaModelDownloaderProps> = ({
  modelId,
  modelName,
  endpoint,
  onDownloadComplete,
  onClose
}) => {
  const [open, setOpen] = useState(false);
  const [customModelName, setCustomModelName] = useState(modelName);
  const [downloading, setDownloading] = useState(false);
  const [downloads, setDownloads] = useState<OllamaModelDownload[]>([]);
  const [currentDownload, setCurrentDownload] = useState<OllamaModelDownload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  // ダウンロード履歴取得
  const fetchDownloads = async () => {
    try {
      const downloadHistory = await ollamaApi.getModelDownloads(modelId);
      setDownloads(downloadHistory);
      
      // 最新の進行中/保留中ダウンロードを見つける
      const activeDownload = downloadHistory.find(d => 
        d.status === OllamaDownloadStatus.DOWNLOADING || 
        d.status === OllamaDownloadStatus.PENDING
      );
      
      if (activeDownload) {
        setCurrentDownload(activeDownload);
        startRefreshInterval(activeDownload.id);
      } else {
        // 最新の完了/失敗したダウンロードを表示
        const latestDownload = downloadHistory[0]; // すでに日付降順でソート済み
        if (latestDownload) {
          setCurrentDownload(latestDownload);
        }
      }
    } catch (err) {
      console.error('Failed to fetch download history:', err);
      setError('ダウンロード履歴の取得に失敗しました');
    }
  };

  // 定期更新処理開始
  const startRefreshInterval = (downloadId: string) => {
    // 既存のインターバルをクリア
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
    
    // 3秒ごとにステータスを更新
    const interval = setInterval(async () => {
      try {
        const status = await ollamaApi.getDownloadStatus(downloadId);
        
        // ステータスログ出力（デバッグ用）
        console.log('ダウンロードステータス更新:', {
          id: status.id,
          model: status.modelName,
          status: status.status,
          progress: status.progress,
          error: status.error
        });
        
        setCurrentDownload(status);
        
        // エラーがある場合は失敗ステータスとして扱う
        const isCompleted = status.status === OllamaDownloadStatus.COMPLETED;
        const isFailed = status.status === OllamaDownloadStatus.FAILED || !!status.error;
        
        // ダウンロードが完了または失敗した場合
        if (isCompleted || isFailed) {
          console.log('ダウンロード終了:', isCompleted ? '成功' : '失敗', status);
          clearInterval(interval);
          setRefreshInterval(null);
          
          // ダウンロード完了時のコールバック (エラーがなく実際に完了した場合のみ)
          if (isCompleted && !status.error && onDownloadComplete) {
            onDownloadComplete();
          }
          
          // 履歴を更新
          fetchDownloads();
        }
      } catch (err) {
        console.error('Failed to update download status:', err);
        clearInterval(interval);
        setRefreshInterval(null);
        setError('ステータスの更新に失敗しました');
      }
    }, 3000);
    
    setRefreshInterval(interval);
  };

  // ダウンロード開始
  const startDownload = async () => {
    try {
      setError(null);
      setDownloading(true);
      
      // モデル名が入力されていることを確認
      if (!customModelName.trim()) {
        setError('モデル名を入力してください');
        setDownloading(false);
        return;
      }
      
      // ダウンロード開始
      const download = await ollamaApi.downloadModel(modelId, customModelName, endpoint);
      setCurrentDownload(download);
      
      // 更新処理開始
      startRefreshInterval(download.id);
      
      // 履歴更新
      fetchDownloads();
    } catch (err: any) {
      console.error('Failed to start download:', err);
      setError(err?.message || 'ダウンロードの開始に失敗しました');
    } finally {
      setDownloading(false);
    }
  };

  // ダイアログ表示/非表示
  const handleOpen = () => {
    setOpen(true);
    fetchDownloads();
  };
  
  const handleClose = () => {
    // インターバルをクリア
    if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
    
    setOpen(false);
    
    if (onClose) {
      onClose();
    }
  };
  
  // ダウンロード履歴再取得
  const handleRefresh = () => {
    fetchDownloads();
  };
  
  // コンポーネントアンマウント時にインターバルクリア
  useEffect(() => {
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  }, [refreshInterval]);

  // ステータスに応じたコンポーネント表示
  const renderStatusInfo = () => {
    if (!currentDownload) {
      return (
        <Alert severity="info">
          ダウンロード履歴がありません。新しいダウンロードを開始してください。
        </Alert>
      );
    }

    const formatSize = (bytes?: number) => {
      if (bytes === undefined) return '0 B';
      if (bytes === 0) return '0 B';
      
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    
    // ステータスのサニティチェック - ステータスが文字列でない場合の対応
    const status = typeof currentDownload.status === 'string' 
      ? currentDownload.status 
      : String(currentDownload.status);
    
    // エラーがある場合は、ステータスに関わらずエラー表示を優先
    if (currentDownload.error) {
      return (
        <Box>
          <Alert severity="error" icon={<ErrorIcon />}>
            ダウンロードに失敗しました
          </Alert>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="error">
              エラー: {currentDownload.error || '不明なエラー'}
            </Typography>
            <Typography variant="body2">
              モデル名: {currentDownload.modelName}
            </Typography>
            <Typography variant="body2">
              失敗日時: {new Date(currentDownload.updatedAt).toLocaleString()}
            </Typography>
          </Box>
        </Box>
      );
    }

    switch (status) {
      case OllamaDownloadStatus.PENDING:
        return (
          <Box>
            <Alert severity="info">ダウンロードを準備中...</Alert>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
              <CircularProgress size={24} sx={{ mr: 2 }} />
              <Typography>マニフェスト取得中</Typography>
            </Box>
          </Box>
        );
        
      case OllamaDownloadStatus.DOWNLOADING:
        return (
          <Box>
            <Alert severity="info">
              ダウンロード中...しばらくお待ちください
            </Alert>
            <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CircularProgress size={24} sx={{ mr: 1 }} />
              <Typography variant="body2">
                モデルをダウンロード中 {currentDownload.progress ? `(${currentDownload.progress}%)` : ''}
              </Typography>
            </Box>
            {currentDownload.totalSize > 0 && (
              <Typography variant="body2" align="center" sx={{ mt: 1 }}>
                {formatSize(currentDownload.downloadedSize)} / {formatSize(currentDownload.totalSize)}
              </Typography>
            )}
          </Box>
        );
        
      case OllamaDownloadStatus.COMPLETED:
        return (
          <Box>
            <Alert severity="success" icon={<FileDownloadDoneIcon />}>
              ダウンロードが完了しました
            </Alert>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2">
                モデル名: {currentDownload.modelName}
              </Typography>
              {currentDownload.modelSizeGb ? (
                <Typography variant="body2">
                  モデルサイズ: {currentDownload.modelSizeGb} GB
                </Typography>
              ) : (
                <Typography variant="body2">
                  ダウンロードサイズ: {formatSize(currentDownload.totalSize)}
                </Typography>
              )}
              <Typography variant="body2">
                完了日時: {new Date(currentDownload.completedAt || currentDownload.updatedAt || '').toLocaleString()}
              </Typography>
            </Box>
          </Box>
        );
        
      case OllamaDownloadStatus.FAILED:
        return (
          <Box>
            <Alert severity="error" icon={<ErrorIcon />}>
              ダウンロードに失敗しました
            </Alert>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="error">
                エラー: {currentDownload.error || '不明なエラー'}
              </Typography>
              <Typography variant="body2">
                モデル名: {currentDownload.modelName}
              </Typography>
              <Typography variant="body2">
                失敗日時: {new Date(currentDownload.updatedAt).toLocaleString()}
              </Typography>
            </Box>
          </Box>
        );
        
      default:
        // 不明なステータスの場合
        return (
          <Box>
            <Alert severity="warning">
              ステータスが不明です: {status}
            </Alert>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2">
                モデル名: {currentDownload.modelName}
              </Typography>
              <Typography variant="body2">
                最終更新: {new Date(currentDownload.updatedAt).toLocaleString()}
              </Typography>
            </Box>
          </Box>
        );
    }
  };

  // ダウンロード履歴の表示
  const renderDownloadHistory = () => {
    if (downloads.length === 0) {
      return null;
    }

    return (
      <Box sx={{ mt: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          ダウンロード履歴
        </Typography>
        <Stack spacing={2}>
          {downloads.map(download => (
            <Paper key={download.id} elevation={1} sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="subtitle2">
                  {download.modelName}
                </Typography>
                {download.status === OllamaDownloadStatus.COMPLETED && (
                  <FileDownloadDoneIcon color="success" />
                )}
                {download.status === OllamaDownloadStatus.DOWNLOADING && (
                  <CircularProgress size={20} />
                )}
                {download.status === OllamaDownloadStatus.FAILED && (
                  <ErrorIcon color="error" />
                )}
                {download.status === OllamaDownloadStatus.PENDING && (
                  <CloudDownloadIcon color="primary" />
                )}
              </Box>
              <Typography variant="caption" color="textSecondary">
                {new Date(download.createdAt).toLocaleString()}
              </Typography>
            </Paper>
          ))}
        </Stack>
      </Box>
    );
  };

  return (
    <>
      <Button
        variant="outlined"
        color="primary"
        onClick={(e) => {
          e.stopPropagation(); // イベントの伝播を停止
          handleOpen();
        }}
        startIcon={<CloudDownloadIcon />}
        size="small"
      >
        モデルをダウンロード
      </Button>

      <Dialog
        open={open}
        onClose={handleClose}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            Ollamaモデルのダウンロード
            <Tooltip title="更新">
              <IconButton onClick={handleRefresh} size="small">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          <Box sx={{ mb: 3 }}>
            <TextField
              label="モデル名"
              value={customModelName}
              onChange={(e) => setCustomModelName(e.target.value)}
              fullWidth
              margin="normal"
              variant="outlined"
              helperText="Ollamaが認識するモデル名を入力してください (例: llama3, mistral-7b)"
              disabled={downloading || currentDownload?.status === OllamaDownloadStatus.DOWNLOADING}
            />
            {endpoint && (
              <Typography variant="caption" color="textSecondary">
                エンドポイント: {endpoint}
              </Typography>
            )}
          </Box>
          
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          <Divider sx={{ my: 2 }} />
          
          <Box sx={{ my: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              ダウンロードステータス
            </Typography>
            {renderStatusInfo()}
          </Box>
          
          {renderDownloadHistory()}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleClose} color="inherit">
            閉じる
          </Button>
          <Button
            onClick={startDownload}
            color="primary"
            variant="contained"
            disabled={downloading || customModelName.trim() === '' || currentDownload?.status === OllamaDownloadStatus.DOWNLOADING}
            startIcon={downloading ? <CircularProgress size={20} /> : <CloudDownloadIcon />}
          >
            {downloading ? 'ダウンロード中...' : 'ダウンロード開始'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default OllamaModelDownloader;