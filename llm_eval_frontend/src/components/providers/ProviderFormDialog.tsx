import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  FormControlLabel,
  Switch,
  Grid,
  Typography,
  CircularProgress
} from '@mui/material';
import { ProviderFormData } from '../../types/provider';

interface ProviderFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: ProviderFormData) => void;
  initialData?: ProviderFormData;
  isSubmitting: boolean;
}

/**
 * プロバイダ追加・編集用のフォームダイアログ
 */
const ProviderFormDialog: React.FC<ProviderFormDialogProps> = ({
  open,
  onClose,
  onSubmit,
  initialData,
  isSubmitting
}) => {
  // デフォルト値の設定
  const defaultData: ProviderFormData = {
    name: '',
    endpoint: '',
    apiKey: '',
    isActive: true
  };

  // フォームの状態
  const [formData, setFormData] = useState<ProviderFormData>(initialData || defaultData);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // initialDataが変更されたらフォームデータを更新
  useEffect(() => {
    if (initialData) {
      console.log('ProviderFormDialog - Updating initialData:', initialData);
      setFormData(initialData);
    }
  }, [initialData]);

  // フォームリセット
  const resetForm = () => {
    setFormData(initialData || defaultData);
    setErrors({});
  };

  // ダイアログを閉じる際の処理
  const handleClose = () => {
    resetForm();
    onClose();
  };

  // 入力値の変更処理
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | { name?: string; value: unknown }>) => {
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

  // バリデーション
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'プロバイダ名は必須です';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // フォーム送信
  const handleSubmit = () => {
    if (validate()) {
      onSubmit(formData);
    }
  };

  // openステータスの変更をログ
  useEffect(() => {
    console.log('ProviderFormDialog - Dialog open state:', open, 'with initialData:', initialData);
  }, [open, initialData]);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {initialData ? 'プロバイダの編集' : 'プロバイダの追加'}
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <TextField
              name="name"
              label="プロバイダ名"
              fullWidth
              value={formData.name}
              onChange={handleChange}
              error={!!errors.name}
              helperText={errors.name || '例: OpenAI, Anthropic など'}
              required
            />
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="endpoint"
              label="エンドポイント"
              fullWidth
              value={formData.endpoint || ''}
              onChange={handleChange}
              error={!!errors.endpoint}
              helperText={errors.endpoint || '例: https://api.openai.com/v1 (オプション)'}
            />
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="apiKey"
              label="APIキー"
              fullWidth
              type="password"
              value={formData.apiKey || ''}
              onChange={handleChange}
              error={!!errors.apiKey}
              helperText={errors.apiKey || '例: OPENAI_API_KEY=sk-xxxx (オプション)'}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              APIキーは環境変数形式 (KEY=VALUE) で設定できます
            </Typography>
          </Grid>
          
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  name="isActive"
                  checked={formData.isActive}
                  onChange={handleSwitchChange}
                  color="primary"
                />
              }
              label="アクティブ"
            />
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
              アクティブなプロバイダのみが評価に使用されます
            </Typography>
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

export default ProviderFormDialog;
