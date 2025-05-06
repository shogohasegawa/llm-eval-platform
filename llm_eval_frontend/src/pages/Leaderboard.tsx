import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  CircularProgress,
  Alert,
  Divider,
  Tab,
  Tabs,
  IconButton,
  Link
} from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { useTheme } from '@mui/material/styles';
import { useAppContext } from '../contexts/AppContext';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`leaderboard-tabpanel-${index}`}
      aria-labelledby={`leaderboard-tab-${index}`}
      {...other}
      style={{ height: '100%' }}
    >
      {value === index && (
        <Box sx={{ height: '100%' }}>
          {children}
        </Box>
      )}
    </div>
  );
}

/**
 * リーダーボードページ
 * 
 * MLflow UIをiframeで埋め込み表示します。
 * ブラウザのセキュリティ制限によりiframeでのアクセスが制限される場合があるため、
 * 直接MLflowにアクセスするオプションも提供します。
 */
const Leaderboard: React.FC = () => {
  const theme = useTheme();
  const { setError } = useAppContext();
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [iframeError, setIframeError] = useState<string | null>(null);

  // タブの変更ハンドラ
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // APIサーバーのURLを取得（環境変数またはウィンドウロケーションから）
  const getApiUrl = () => {
    // 環境変数が設定されていればそれを使用、なければホスト名からURLを構築
    const apiUrl = import.meta.env.VITE_API_BASE_URL || `http://${window.location.hostname}:8001`;
    return apiUrl;
  };

  // MLflowへの直接アクセスURLを取得
  const getMlflowDirectUrl = () => {
    return `${getApiUrl()}/proxy-mlflow/`;
  };

  // APIを通じたMLflowへのプロキシURLを取得
  const getMlflowProxyUrl = () => {
    return `${getApiUrl()}/proxy-mlflow/`;
  };

  // MLflow UIをiframeで表示するためのURL
  const getMlflowUiUrl = () => {
    // MLflowのカスタムUIページのパスを返す
    return `${getApiUrl()}/mlflow-ui`;
    
    // 直接MLflowに接続する場合はこちらを使用（デバッグ用）
    // return 'http://localhost:5000';
  };

  // iframeのonLoadハンドラ
  const handleIframeLoad = () => {
    setLoading(false);
  };

  // iframeのonErrorハンドラ
  const handleIframeError = () => {
    setLoading(false);
    setIframeError('MLflow UIの読み込みに失敗しました。');
  };

  // 外部リンクを新しいタブで開く
  const openExternalLink = (url: string) => {
    window.open(url, '_blank', 'noopener');
  };

  // MLflowへの接続をテスト
  useEffect(() => {
    const testMlflowConnection = async () => {
      try {
        // HEADではなくGETメソッドを使用（多くのプロキシはHEADをサポートしていない）
        const response = await fetch(getMlflowProxyUrl(), { 
          method: 'GET',
          headers: {
            'Cache-Control': 'no-cache'
          }
        });
        if (!response.ok) {
          setIframeError(`MLflowへの接続に問題があります（ステータス: ${response.status}）`);
        } else {
          console.log('MLflow接続テスト成功:', response.status);
        }
      } catch (err) {
        console.error('MLflow接続テストエラー:', err);
        setIframeError('MLflowサーバーに接続できません。サーバーが起動していることを確認してください。');
      }
    };

    testMlflowConnection();
  }, []);

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 70px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        mb: 2
      }}>
        <Typography variant="h4" component="h1">
          リーダーボード (MLflow)
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<OpenInNewIcon />}
            onClick={() => openExternalLink(getMlflowProxyUrl())}
          >
            新しいタブで開く
          </Button>
          
          <Button
            variant="outlined"
            startIcon={<FileDownloadIcon />}
            onClick={() => window.location.reload()}
          >
            再読み込み
          </Button>
        </Box>
      </Box>

      <Divider sx={{ mb: 2 }} />
      
      {iframeError && (
        <Alert 
          severity="warning" 
          sx={{ mb: 2 }}
          action={
            <Button 
              color="inherit" 
              size="small"
              onClick={() => window.location.reload()}
            >
              再読み込み
            </Button>
          }
        >
          {iframeError}
        </Alert>
      )}
      
      <Paper 
        elevation={2} 
        sx={{ 
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          overflow: 'hidden',
          bgcolor: theme.palette.background.paper
        }}
      >
        {loading && (
          <Box sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'rgba(255, 255, 255, 0.7)',
            zIndex: 10
          }}>
            <Box sx={{ textAlign: 'center' }}>
              <CircularProgress sx={{ mb: 2 }} />
              <Typography variant="body1">
                MLflow UIを読み込み中...
              </Typography>
            </Box>
          </Box>
        )}
        
        <iframe
          src={getMlflowUiUrl()}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            flex: 1,
          }}
          title="MLflow Dashboard"
          onLoad={handleIframeLoad}
          onError={handleIframeError}
        />
      </Paper>
    </Box>
  );
};

export default Leaderboard;
