import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  CircularProgress,
  Divider,
  Link,
  Alert,
  Snackbar
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { useTheme } from '@mui/material/styles';

/**
 * リーダーボードページ
 *
 * MLflow UIを埋め込み表示します。
 */
const Leaderboard: React.FC = () => {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [iframeLoading, setIframeLoading] = useState(true);
  const [mlflowDirectAccessOk, setMlflowDirectAccessOk] = useState<boolean | null>(null);
  const [mlflowProxyAccessOk, setMlflowProxyAccessOk] = useState<boolean | null>(null);
  const [mlflowStatus, setMlflowStatus] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showError, setShowError] = useState(false);
  const [messageType, setMessageType] = useState<'error' | 'success' | 'info'>('error');

  /**
   * MLflow関連のURLを生成する関数
   * システム全体で一貫した接続設定を使用するために統合
   */
  const getMlflowEndpoints = () => {
    // ベースとなるAPI URL
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ||
      (import.meta.env.DEV ? 'http://localhost:8001' : 'http://llm-api-backend:8000');

    // 各種エンドポイント
    // 外部URLは環境変数から取得、未設定の場合はデフォルト値を使用
    // VITE_MLFLOW_DIRECT_URLはMLFLOW_EXTERNAL_URIから設定される共通の外部URI
    const directUrl = import.meta.env.VITE_MLFLOW_DIRECT_URL || 'http://localhost:5001';
    const proxyEndpoint = import.meta.env.VITE_MLFLOW_PROXY_ENDPOINT || '/proxy-mlflow';

    // MLflowの内部設定（デバッグ情報用、実際の接続には使用されない）
    const mlflowHost = import.meta.env.MLFLOW_HOST || 'llm-mlflow-tracking';
    const mlflowPort = import.meta.env.MLFLOW_PORT || '5000';

    return {
      // ブラウザからの直接アクセス用URL
      directUrl,

      // APIサーバー経由のプロキシURL
      proxyUrl: `${apiBaseUrl}${proxyEndpoint}`,

      // 標準MLflow APIエンドポイント (接続テスト用)
      mlflowApiEndpoint: '/api/2.0/mlflow/experiments/list',

      // バックエンド内部接続用URL（デバッグ情報用）
      internalUrl: `http://${mlflowHost}:${mlflowPort}`
    };
  };

  // 外部リンクを新しいタブで開く
  const openExternalLink = (url: string) => {
    window.open(url, '_blank', 'noopener');
  };

  // MLflowを直接開く
  const openMlflow = () => {
    const { directUrl } = getMlflowEndpoints();
    openExternalLink(directUrl);
  };

  // MLflowへの接続をテスト（シンプル化したアプローチ - 標準APIエンドポイントを使用）
  const testMlflowConnection = async () => {
    setLoading(true);
    try {
      // 環境変数設定を明示的にログ出力（デバッグ用）
      console.log('🔍 環境変数設定値:', {
        VITE_DEV_SKIP_API_CHECK: import.meta.env.VITE_DEV_SKIP_API_CHECK,
        VITE_DEV_FORCE_MLFLOW_OK: import.meta.env.VITE_DEV_FORCE_MLFLOW_OK,
        DEV: import.meta.env.DEV
      });

      // 環境変数設定に基づき、API検証をスキップするかどうか判断
      const skipApiCheckValue = import.meta.env.VITE_DEV_SKIP_API_CHECK;
      const forceMlflowOkValue = import.meta.env.VITE_DEV_FORCE_MLFLOW_OK;
      const skipApiCheck = skipApiCheckValue === 'true';
      const forceMlflowOk = forceMlflowOkValue === 'true';

      // スキップフラグをログ出力
      console.log('⚙️ 接続チェック設定:', {
        skipApiCheck,
        forceMlflowOk,
        rawSkipValue: skipApiCheckValue,
        rawForceValue: forceMlflowOkValue
      });

      // MLflowエンドポイント情報を取得
      const mlflowEndpoints = getMlflowEndpoints();

      // 環境変数設定に基づき接続チェックをスキップするか判断
      if (skipApiCheck || forceMlflowOk) {
        console.log('⚠️ MLflow API接続チェックをスキップします（skipApiCheck=' + skipApiCheck + ', forceMlflowOk=' + forceMlflowOk + '）');
        setMlflowDirectAccessOk(true);
        setMlflowProxyAccessOk(true);
        setMlflowStatus({ status: 'ok', message: '接続チェックスキップ（開発モード）' });
      } else {
        console.log('✅ MLflow API接続チェックを実行します');

        // 1. まず直接接続を試みる（標準MLflow APIエンドポイント使用）
        try {
          const mlflowApiEndpoint = `${mlflowEndpoints.directUrl}${mlflowEndpoints.mlflowApiEndpoint}`;
          console.log('MLflow直接接続テスト:', mlflowApiEndpoint);

          const directResponse = await fetch(mlflowApiEndpoint);

          if (directResponse.ok) {
            console.log('MLflow直接接続成功！');
            setMlflowDirectAccessOk(true);
            setMlflowProxyAccessOk(false); // プロキシは使用しない
            setMlflowStatus({
              status: 'ok',
              message: 'MLflowに直接接続しています',
              directOnly: true
            });
          } else {
            console.error('MLflow直接接続エラー:', directResponse.statusText);
            setMlflowDirectAccessOk(false);

            // 2. 直接接続に失敗した場合、プロキシ接続を試みる
            console.log('直接接続に失敗しました。プロキシ経由での接続を試みます。');
            await testMlflowProxyConnection(mlflowEndpoints);
          }
        } catch (directError) {
          console.error('MLflow直接接続例外:', directError);
          setMlflowDirectAccessOk(false);

          // 直接接続で例外が発生した場合も、プロキシ接続を試みる
          console.log('直接接続で例外が発生しました。プロキシ経由での接続を試みます。');
          await testMlflowProxyConnection(mlflowEndpoints);
        }
      }

      // URL情報を出力（デバッグ用）
      console.log('MLflow接続情報:', mlflowEndpoints);
    } catch (error) {
      console.error('MLflow接続テスト全体エラー:', error);
      setMlflowDirectAccessOk(false);
      setMlflowProxyAccessOk(false);
      setMlflowStatus({
        status: 'error',
        message: '接続エラー: MLflowサーバーに接続できません'
      });
    } finally {
      setLoading(false);
    }
  };

  // プロキシ経由でのMLflow接続をテスト（ヘルパー関数）
  const testMlflowProxyConnection = async (mlflowEndpoints: any) => {
    try {
      // プロキシエンドポイント経由でMLflowのexperiments/listにアクセス
      const proxyApiEndpoint = `${mlflowEndpoints.proxyUrl}${mlflowEndpoints.mlflowApiEndpoint}`;
      console.log('MLflowプロキシ接続テスト:', proxyApiEndpoint);

      const proxyResponse = await fetch(proxyApiEndpoint);

      if (proxyResponse.ok) {
        console.log('MLflowプロキシ接続成功！');
        setMlflowProxyAccessOk(true);
        setMlflowDirectAccessOk(false); // 直接接続は使用しない
        setMlflowStatus({
          status: 'ok',
          message: 'MLflowにプロキシ経由で接続しています',
          proxyOnly: true
        });
      } else {
        console.error('MLflowプロキシ接続エラー:', proxyResponse.statusText);
        setMlflowProxyAccessOk(false);
        setMlflowStatus({
          status: 'error',
          message: `プロキシ接続エラー: ${proxyResponse.status} ${proxyResponse.statusText}`
        });
      }
    } catch (proxyError) {
      console.error('MLflowプロキシ接続例外:', proxyError);
      setMlflowProxyAccessOk(false);
      setMlflowStatus({
        status: 'error',
        message: `プロキシ接続例外: ${proxyError}`
      });
    }
  };

  // iframe読み込みエラーを処理する関数
  const handleIframeError = (e: React.SyntheticEvent<HTMLIFrameElement>) => {
    console.error('MLflow iframe 読み込みエラー', e);
    setIframeLoading(false);
    setErrorMessage('MLflowダッシュボードの読み込みに失敗しました。別タブで開くボタンをお試しください。');
    setMessageType('error');
    setShowError(true);
  };

  // iframe読み込み完了を処理する関数
  const handleIframeLoad = (e: React.SyntheticEvent<HTMLIFrameElement>) => {
    console.log('MLflow iframe 読み込み完了');
    setIframeLoading(false);
  };

  // コンポーネントマウント時に接続テスト実行
  useEffect(() => {
    testMlflowConnection();
  }, []);

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 70px)', display: 'flex', flexDirection: 'column' }}>
      <Divider sx={{ mb: 2 }} />
      
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
            <CircularProgress />
          </Box>
        )}
        
        <Box sx={{ p: 2 }}>
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            mb: 2 
          }}>
            <Typography variant="h5">
              MLflow ダッシュボード
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              {mlflowDirectAccessOk === true && (
                <span style={{ color: 'green', fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
                  ✓ MLflow接続OK
                </span>
              )}
              {mlflowDirectAccessOk === false && (
                <span style={{ color: 'red', fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
                  ✗ MLflow接続エラー
                </span>
              )}
              <Button
                variant="outlined"
                size="small"
                startIcon={<OpenInNewIcon />}
                onClick={openMlflow}
              >
                新しいタブで開く
              </Button>
            </Box>
          </Box>
          
          {mlflowProxyAccessOk === false && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              MLflowサーバーへの接続に問題があります。バックエンドの設定を確認してください。
            </Alert>
          )}
        </Box>
        
        {/* MLflowダッシュボードのiframe埋め込み */}
        <Box sx={{
          flex: 1,
          position: 'relative',
          display: 'flex',
          overflow: 'hidden',
          borderTop: '1px solid #e0e0e0'
        }}>
          {mlflowDirectAccessOk === true ? (
            <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
              {iframeLoading && (
                <Box sx={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: 'rgba(255, 255, 255, 0.9)',
                  zIndex: 5
                }}>
                  <CircularProgress size={40} />
                  <Typography variant="body2" sx={{ mt: 2 }}>
                    MLflowダッシュボードを読み込み中...
                  </Typography>
                </Box>
              )}
              <iframe
                src={getMlflowEndpoints().directUrl}
                title="MLflow Dashboard"
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  flexGrow: 1
                }}
                referrerPolicy="origin"
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation allow-storage-access-by-user-activation"
                onError={handleIframeError}
                onLoad={handleIframeLoad}
              />
            </Box>
          ) : (
            <Box sx={{ 
              p: 4, 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center',
              height: '100%',
              width: '100%',
              bgcolor: '#f5f5f5' 
            }}>
              <Typography variant="h6" gutterBottom color="error">
                MLflowダッシュボードに接続できません
              </Typography>
              <Typography variant="body1" paragraph align="center" sx={{ maxWidth: '800px', mb: 3 }}>
                MLflowサーバーに接続できませんでした。サーバーが起動しているか確認してください。
              </Typography>
              
              <Box sx={{ 
                p: 2, 
                border: '1px solid #e0e0e0', 
                borderRadius: 1,
                bgcolor: theme.palette.background.paper, 
                maxWidth: '800px',
                width: '100%'
              }}>
                <Typography variant="h6" gutterBottom align="center">
                  MLflowアクセス情報
                </Typography>
                
                <Box sx={{ 
                  mb: 2, 
                  p: 1.5, 
                  bgcolor: '#f8f8f8', 
                  borderRadius: 1,
                  border: '1px dashed #ccc'
                }}>
                  <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <strong>MLflow URL：</strong>
                    <Box component="span" sx={{ 
                      display: 'inline-block', 
                      p: '4px 8px',
                      bgcolor: '#e8f4f8', 
                      borderRadius: '4px',
                      fontFamily: 'monospace',
                      fontSize: '0.9rem',
                      fontWeight: 'medium'
                    }}>
                      {getMlflowEndpoints().directUrl}
                    </Box>
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => {
                        navigator.clipboard.writeText(getMlflowEndpoints().directUrl);
                        setErrorMessage('URLをクリップボードにコピーしました');
                        setMessageType('success');
                        setShowError(true);
                      }}
                      sx={{ minWidth: 'auto', p: '2px 4px' }}
                    >
                      コピー
                    </Button>
                  </Typography>
                </Box>
              </Box>
            </Box>
          )}
        </Box>
      </Paper>

      <Snackbar
        open={showError}
        autoHideDuration={4000}
        onClose={() => setShowError(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setShowError(false)} severity={messageType} sx={{ width: '100%' }}>
          {errorMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Leaderboard;