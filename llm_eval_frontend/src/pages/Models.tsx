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
  Divider
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import { useModels } from '../hooks/useProviders';
import ModelCard from '../components/providers/ModelCard';
import { useAppContext } from '../contexts/AppContext';

/**
 * LLMモデル一覧ページ
 */
const Models: React.FC = () => {
  // 状態管理
  const [searchTerm, setSearchTerm] = useState('');
  
  // コンテキストから状態取得
  const { setError } = useAppContext();
  
  // モデルデータ取得
  const { data: models, isLoading, isError, error } = useModels();
  
  // エラーハンドリング
  if (error) {
    setError(`モデル一覧の取得に失敗しました: ${error.message}`);
  }
  
  // 検索条件でモデルをフィルタリング
  const filteredModels = models ? models.filter(model => {
    const term = searchTerm.toLowerCase();
    return (
      model.name.toLowerCase().includes(term) ||
      (model.displayName && model.displayName.toLowerCase().includes(term))
    );
  }) : [];
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          LLMモデル管理
        </Typography>
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
              <ModelCard model={model} />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Alert severity="info">
          {searchTerm ? 
            '検索条件に一致するモデルが見つかりませんでした。' : 
            'モデルが登録されていません。プロバイダページからモデルを追加してください。'
          }
        </Alert>
      )}
    </Box>
  );
};

export default Models;