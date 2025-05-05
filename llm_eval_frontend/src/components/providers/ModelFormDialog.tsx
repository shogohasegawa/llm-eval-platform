import React, { useState, useEffect } from 'react';
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
  FormHelperText,
  Switch,
  FormControlLabel,
  Grid,
  CircularProgress,
  SelectChangeEvent,
  Typography
} from '@mui/material';
import { ModelFormData, Provider } from '../../types/provider';
import { useProviders } from '../../hooks/useProviders';

interface ModelFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: ModelFormData) => void;
  initialData?: ModelFormData;
  isSubmitting: boolean;
}

/**
 * モデル追加・編集用のフォームダイアログ
 */
const ModelFormDialog: React.FC<ModelFormDialogProps> = ({
  open,
  onClose,
  onSubmit,
  initialData,
  isSubmitting
}) => {
  // デフォルト値の設定
  const defaultData: ModelFormData = {
    providerId: '',
    name: '',
    displayName: '',
    description: '',
    endpoint: '',
    apiKey: '',
    parameters: {},
    isActive: true
  };

  // プロバイダデータの取得
  const { data: providers, isLoading: isLoadingProviders, isError, error } = useProviders();
  
  // プロバイダデータのデバッグ
  console.log('Model form - Providers data:', providers);
  console.log('Model form - Loading providers:', isLoadingProviders);
  console.log('Model form - Provider error:', isError, error);

  // フォームの状態
  const [formData, setFormData] = useState<ModelFormData>(initialData || defaultData);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [parametersString, setParametersString] = useState<string>(
    initialData?.parameters ? JSON.stringify(initialData.parameters, null, 2) : '{}'
  );

  // 選択されたプロバイダの情報
  const selectedProvider = formData.providerId 
    ? providers?.find(p => p.id === formData.providerId) 
    : undefined;

  // プロバイダが変更されたら、エンドポイントとAPIキーを自動設定
  useEffect(() => {
    if (selectedProvider && !initialData) {
      setFormData(prev => ({
        ...prev,
        endpoint: selectedProvider.endpoint || '',
        apiKey: selectedProvider.apiKey || ''
      }));
    }
  }, [selectedProvider, initialData]);

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

  // プロバイダの変更処理
  const handleProviderChange = (e: SelectChangeEvent<string>) => {
    const providerId = e.target.value;
    
    // 選択されたプロバイダを取得
    const provider = providers?.find(p => p.id === providerId);
    
    setFormData(prev => ({
      ...prev,
      providerId,
      // プロバイダのエンドポイントとAPIキーを自動設定
      endpoint: provider?.endpoint || '',
      apiKey: provider?.apiKey || ''
    }));
    
    // エラーをクリア
    if (errors.providerId) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors.providerId;
        return newErrors;
      });
    }
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
    
    if (!formData.providerId) {
      newErrors.providerId = 'プロバイダは必須です';
    }
    
    if (!formData.name.trim()) {
      newErrors.name = 'モデル名は必須です';
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
      
      // 表示名が空の場合は、モデル名を使用
      const displayName = formData.displayName.trim() || formData.name;
      
      // 送信前データを確認
      const submitData = {
        ...formData,
        displayName,
        parameters,
        providerId: formData.providerId, // 明示的に指定
        isActive: !!formData.isActive, // ブール値に変換して送信
        // バックエンドがスネークケースを期待する可能性があるため、両方のフォーマットで送信
        provider_id: formData.providerId,
        display_name: displayName,
        is_active: !!formData.isActive,
        api_key: formData.apiKey?.trim() || undefined
      };
      
      console.log('モデル送信データ:', submitData);
      console.log('選択されたプロバイダ:', selectedProvider);
      
      onSubmit(submitData);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {initialData ? 'モデルの編集' : 'モデルの追加'}
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <FormControl fullWidth required error={!!errors.providerId}>
              <InputLabel>プロバイダ</InputLabel>
              <Select
                name="providerId"
                value={formData.providerId}
                onChange={handleProviderChange}
                label="プロバイダ"
                disabled={isLoadingProviders || !!initialData}
              >
                {isLoadingProviders && (
                  <MenuItem disabled>読み込み中...</MenuItem>
                )}
                {!isLoadingProviders && providers && providers.length === 0 && (
                  <MenuItem disabled>利用可能なプロバイダがありません</MenuItem>
                )}
                {providers?.map((provider) => (
                  <MenuItem key={provider.id} value={provider.id}>
                    {provider.name}
                  </MenuItem>
                ))}
              </Select>
              {errors.providerId && <FormHelperText>{errors.providerId}</FormHelperText>}
              {initialData && (
                <FormHelperText>編集時にプロバイダは変更できません</FormHelperText>
              )}
              {!initialData && !isLoadingProviders && (!providers || providers.length === 0) && (
                <FormHelperText error>
                  利用可能なプロバイダがありません。先にプロバイダを追加してください。
                </FormHelperText>
              )}
            </FormControl>
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="name"
              label="モデル名"
              fullWidth
              value={formData.name}
              onChange={handleChange}
              error={!!errors.name}
              helperText={errors.name || 'APIで使用される内部モデル名（例: gpt-4, claude-3-sonnet）'}
              required
            />
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="displayName"
              label="表示名"
              fullWidth
              value={formData.displayName}
              onChange={handleChange}
              error={!!errors.displayName}
              helperText={errors.displayName || 'UIに表示される名前（例: GPT-4, Claude 3 Sonnet） - 未入力時はモデル名が使用されます'}
            />
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="description"
              label="説明"
              fullWidth
              multiline
              rows={2}
              value={formData.description || ''}
              onChange={handleChange}
              helperText="モデルの説明（オプション）"
            />
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="endpoint"
              label="エンドポイント"
              fullWidth
              value={formData.endpoint}
              onChange={handleChange}
              error={!!errors.endpoint}
              helperText={errors.endpoint || 'プロバイダから自動設定されます'}
              disabled={true}
            />
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
              モデルのエンドポイントはプロバイダの設定から自動的に取得されます
            </Typography>
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              name="apiKey"
              label="APIキー"
              fullWidth
              type="password"
              value={formData.apiKey}
              onChange={handleChange}
              error={!!errors.apiKey}
              helperText={errors.apiKey || 'プロバイダから自動設定されます'}
              disabled={true}
            />
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
              APIキーはプロバイダの設定から自動的に取得されます
            </Typography>
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
              helperText={errors.parameters || 'モデルのパラメータをJSON形式で入力（例: {"temperature": 0.7, "max_tokens": 1000}）'}
              InputProps={{
                sx: { fontFamily: 'monospace' }
              }}
            />
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
              アクティブなモデルのみが評価に使用されます
            </Typography>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>キャンセル</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={isSubmitting || (!providers || providers.length === 0) || !formData.providerId}
          startIcon={isSubmitting ? <CircularProgress size={20} /> : null}
        >
          {initialData ? '更新' : '追加'}
          {!formData.providerId && providers && providers.length > 0 && ' (プロバイダを選択してください)'}
          {(!providers || providers.length === 0) && ' (先にプロバイダを追加してください)'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModelFormDialog;
