import React, { useState } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button, 
  TextField, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  Grid,
  CircularProgress,
  FormControlLabel,
  Switch,
  FormHelperText,
  SelectChangeEvent
} from '@mui/material';
import { MetricFormData, MetricType } from '../../types/metrics';

interface MetricFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: MetricFormData) => void;
  initialData?: MetricFormData;
  isSubmitting: boolean;
}

/**
 * 評価指標追加・編集用のフォームダイアログ
 */
const MetricFormDialog: React.FC<MetricFormDialogProps> = ({
  open,
  onClose,
  onSubmit,
  initialData,
  isSubmitting
}) => {
  // デフォルト値の設定
  const defaultData: MetricFormData = {
    name: '',
    type: 'accuracy',
    description: '',
    isHigherBetter: true,
    parameters: {}
  };

  // フォームの状態
  const [formData, setFormData] = useState<MetricFormData>(initialData || defaultData);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [parametersString, setParametersString] = useState<string>(
    initialData?.parameters ? JSON.stringify(initialData.parameters, null, 2) : '{}'
  );

  // フォームリセット
  const resetForm = () => {
    setFormData(initialData || defaultData);
    setParametersString(initialData?.parameters ? JSON.stringify(initialData.parameters, null, 2) : '{}');
    setErrors({});
  };

  // ダイアログを閉じる際の処理
  const handleClose = () => {
    resetForm();
    onClose();
  };

  // 入力値の変更処理
  const handleChange = (e: React.ChangeEvent<HTMLInputElement> | SelectChangeEvent<string>) => {
    const { name, value } = e.target;
    if (name) {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
      
      // エラーをクリア
      if (errors[name]) {
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[name];
          return newErrors;
        });
      }
    }
  };

  // スイッチの変更処理
  const handleSwitchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: checked
    }));
  };

  // パラメータの変更処理
  const handleParametersChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setParametersString(e.target.value);
    
    // エラーをクリア
    if (errors.parameters) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors.parameters;
        return newErrors;
      });
    }
  };

  // バリデーション
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = '名前は必須です';
    }
    
    // パラメータのJSONバリデーション
    try {
      if (parametersString.trim()) {
        JSON.parse(parametersString);
      }
    } catch (e) {
      newErrors.parameters = 'パラメータは有効なJSON形式である必要があります';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // フォーム送信
  const handleSubmit = () => {
    if (validate()) {
      // パラメータをJSONオブジェクトに変換
      let parameters = {};
      try {
        if (parametersString.trim()) {
          parameters = JSON.parse(parametersString);
        }
      } catch (e) {
        // バリデーションで既にチェック済みなので、ここでは無視
      }
      
      onSubmit({
        ...formData,
        parameters
      });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {initialData ? '評価指標の編集' : '評価指標の追加'}
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <TextField
              name="name"
              label="評価指標名"
              fullWidth
              value={formData.name}
              onChange={handleChange}
              error={!!errors.name}
              helperText={errors.name}
              required
            />
          </Grid>
          
          <Grid item xs={12}>
            <FormControl fullWidth required>
              <InputLabel>タイプ</InputLabel>
              <Select
                name="type"
                value={formData.type}
                onChange={handleChange}
                label="タイプ"
              >
                <MenuItem value="accuracy">精度 (Accuracy)</MenuItem>
                <MenuItem value="precision">適合率 (Precision)</MenuItem>
                <MenuItem value="recall">再現率 (Recall)</MenuItem>
                <MenuItem value="f1">F1スコア (F1)</MenuItem>
                <MenuItem value="bleu">BLEU</MenuItem>
                <MenuItem value="rouge">ROUGE</MenuItem>
                <MenuItem value="exact_match">完全一致 (Exact Match)</MenuItem>
                <MenuItem value="semantic_similarity">意味的類似度 (Semantic Similarity)</MenuItem>
                <MenuItem value="latency">レイテンシ (Latency)</MenuItem>
                <MenuItem value="token_count">トークン数 (Token Count)</MenuItem>
                <MenuItem value="custom">カスタム (Custom)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="description"
              label="説明"
              fullWidth
              multiline
              rows={3}
              value={formData.description || ''}
              onChange={handleChange}
              helperText="評価指標の説明（オプション）"
            />
          </Grid>
          
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  name="isHigherBetter"
                  checked={formData.isHigherBetter}
                  onChange={handleSwitchChange}
                  color="primary"
                />
              }
              label="値が高いほど良い"
            />
            <FormHelperText>
              この評価指標は値が高いほど良いパフォーマンスを示す場合はオン、低いほど良い場合はオフにしてください
            </FormHelperText>
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="parameters"
              label="パラメータ (JSON)"
              fullWidth
              multiline
              rows={4}
              value={parametersString}
              onChange={handleParametersChange}
              error={!!errors.parameters}
              helperText={errors.parameters || '評価指標のパラメータをJSON形式で入力（例: {"threshold": 0.5}）'}
              InputProps={{
                sx: { fontFamily: 'monospace' }
              }}
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>キャンセル</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={20} /> : null}
        >
          {initialData ? '更新' : '追加'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MetricFormDialog;
