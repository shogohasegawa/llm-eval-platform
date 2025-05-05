import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Card,
  CardContent,
  Grid,
  Divider,
  CircularProgress,
  Alert,
  Badge,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { useDatasetByName } from '../hooks/useDatasets';
import { DatasetItem } from '../types/dataset';
import { useAppContext } from '../contexts/AppContext';

/**
 * データセット詳細ページコンポーネント
 */
const DatasetDetail: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { setError } = useAppContext();

  // 展開状態を管理
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  // データセット詳細の取得
  const {
    data: dataset,
    isLoading,
    isError,
    error,
  } = useDatasetByName(id || '');

  // エラーハンドリング
  if (error) {
    setError(`データセットの取得に失敗しました: ${error.message}`);
  }

  // 戻るボタンのハンドラ
  const handleGoBack = () => {
    navigate('/datasets');
  };

  // アイテムの展開/折りたたみを切り替える
  const toggleItemExpand = (itemId: string) => {
    setExpandedItems((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }));
  };

  // データセットタイプに応じた色を設定
  const getDatasetTypeColor = (type: string) => {
    switch (type) {
      case 'test':
        return '#4CAF50';
      case 'n_shot':
        return '#2196F3';
      default:
        return '#757575';
    }
  };

  // JSONを整形して表示
  const formatJson = (value: any) => {
    if (!value) return '';
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  // テキストを省略表示
  const truncateText = (text: string | undefined, maxLength: number) => {
    if (!text) return '-';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" my={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (isError || !dataset) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          データセットの取得中にエラーが発生したか、データセットが見つかりませんでした。
        </Alert>
        <Box mt={2}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleGoBack}
          >
            データセット一覧に戻る
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" alignItems="center" mb={3}>
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={handleGoBack}
          sx={{ mr: 2 }}
        >
          戻る
        </Button>
        <Typography variant="h4" component="h1">
          {dataset.name}
        </Typography>
      </Box>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Box mb={2}>
                <Typography variant="subtitle1" component="div" gutterBottom>
                  基本情報
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  <strong>名前:</strong> {dataset.name}
                </Typography>
                {dataset.description && (
                  <Typography variant="body2" color="text.secondary" paragraph>
                    <strong>説明:</strong> {dataset.description}
                  </Typography>
                )}
                <Typography variant="body2" color="text.secondary" paragraph>
                  <strong>タイプ:</strong>{' '}
                  <Chip
                    label={dataset.type}
                    size="small"
                    sx={{
                      backgroundColor: getDatasetTypeColor(dataset.type),
                      color: 'white',
                    }}
                  />
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>アイテム数:</strong> {dataset.items.length}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box mb={2}>
                <Typography variant="subtitle1" component="div" gutterBottom>
                  ファイル情報
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  <strong>ファイルパス:</strong> {dataset.file_path}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>作成日時:</strong>{' '}
                  {new Date(dataset.created_at || dataset.createdAt || '').toLocaleString()}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Typography variant="h5" component="h2" gutterBottom>
        データセットアイテム
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>指示</TableCell>
              <TableCell>入力</TableCell>
              <TableCell>出力</TableCell>
              <TableCell>詳細</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {dataset.items.map((item: DatasetItem) => (
              <React.Fragment key={item.id}>
                <TableRow hover>
                  <TableCell>{item.id}</TableCell>
                  <TableCell>{truncateText(item.instruction, 50)}</TableCell>
                  <TableCell>{truncateText(item.input, 50)}</TableCell>
                  <TableCell>{truncateText(item.output, 50)}</TableCell>
                  <TableCell>
                    <IconButton
                      onClick={() => toggleItemExpand(item.id)}
                      size="small"
                    >
                      {expandedItems[item.id] ? (
                        <ExpandLessIcon />
                      ) : (
                        <Badge
                          color="primary"
                          variant="dot"
                          invisible={!item.additional_data || Object.keys(item.additional_data).length === 0}
                        >
                          <ExpandMoreIcon />
                        </Badge>
                      )}
                    </IconButton>
                  </TableCell>
                </TableRow>
                {expandedItems[item.id] && (
                  <TableRow>
                    <TableCell colSpan={5} sx={{ py: 0 }}>
                      <Box sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          詳細情報
                        </Typography>
                        <Grid container spacing={2}>
                          {item.input && (
                            <Grid item xs={12} md={6}>
                              <Typography variant="caption" component="div" fontWeight="bold">
                                入力（完全）
                              </Typography>
                              <Paper sx={{ p: 1, maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                                {item.input}
                              </Paper>
                            </Grid>
                          )}
                          {item.output && (
                            <Grid item xs={12} md={6}>
                              <Typography variant="caption" component="div" fontWeight="bold">
                                出力（完全）
                              </Typography>
                              <Paper sx={{ p: 1, maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                                {item.output}
                              </Paper>
                            </Grid>
                          )}
                          {item.additional_data && Object.keys(item.additional_data).length > 0 && (
                            <Grid item xs={12}>
                              <Typography variant="caption" component="div" fontWeight="bold">
                                追加データ
                              </Typography>
                              <Paper sx={{ p: 1, maxHeight: 300, overflow: 'auto' }}>
                                <pre>{formatJson(item.additional_data)}</pre>
                              </Paper>
                            </Grid>
                          )}
                        </Grid>
                      </Box>
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default DatasetDetail;
