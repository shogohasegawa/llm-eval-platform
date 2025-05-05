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
  Grid,
  CircularProgress,
  FormControlLabel,
  Switch,
  FormHelperText,
  SelectChangeEvent,
  Typography,
  Box,
  Alert
} from '@mui/material';
import { MetricFormData, MetricType, MetricTypeInfo } from '../../types/metrics';
import { useMetricTypes } from '../../hooks/useMetrics';

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
    type: '',
    description: '',
    isHigherBetter: true, // 初期値はtrueにして明示的に指定
    is_higher_better: true, // スネークケース版も設定 (バックエンド用)
    parameters: {}
  };

  // APIからメトリックタイプを取得
  const { data: metricTypes, isLoading: isLoadingMetricTypes, error: metricTypesError } = useMetricTypes();

  // フォームの状態
  const [formData, setFormData] = useState<MetricFormData>(initialData || defaultData);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [parametersString, setParametersString] = useState<string>(
    initialData?.parameters ? JSON.stringify(initialData.parameters, null, 2) : '{}'
  );

  // 選択されたメトリックタイプの情報
  const [selectedMetricTypeInfo, setSelectedMetricTypeInfo] = useState<MetricTypeInfo | null>(null);

  // メトリックタイプを初期設定
  useEffect(() => {
    if (metricTypes && metricTypes.length > 0 && !initialData && !formData.type) {
      setFormData(prev => ({
        ...prev,
        type: metricTypes[0].name,
        isHigherBetter: metricTypes[0].is_higher_better
      }));
    }
  }, [metricTypes, initialData, formData.type]);

  // 選択されているメトリックタイプの情報を更新
  useEffect(() => {
    if (metricTypes && formData.type) {
      const selected = metricTypes.find(mt => mt.name === formData.type);
      setSelectedMetricTypeInfo(selected || null);
      
      // タイプが変更された場合、isHigherBetterも自動的に同期
      if (selected) {
        console.log("メトリクスタイプを選択:", selected.name, "is_higher_better:", selected.is_higher_better);
        // is_higher_betterをブール値として確実に取得
        const isHigherBetterValue = !!selected.is_higher_better;
        
        setFormData(prev => ({
          ...prev,
          isHigherBetter: isHigherBetterValue,
          is_higher_better: isHigherBetterValue // スネークケース版も設定
        }));
      }
    }
  }, [metricTypes, formData.type]);

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
    
    if (!formData.type) {
      newErrors.type = 'タイプは必須です';
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
      
      // isHigherBetterを明示的にブール値に変換
      const isHigherBetterValue = !!formData.isHigherBetter;
      
      // 送信前にconsoleで値を確認
      console.log("送信するフォームデータ:", {
        ...formData,
        parameters,
        isHigherBetter: isHigherBetterValue,
        "formData.isHigherBetter元の値": formData.isHigherBetter,
        "formData.isHigherBetter元の型": typeof formData.isHigherBetter
      });
      
      onSubmit({
        ...formData,
        parameters,
        isHigherBetter: isHigherBetterValue, // 明示的にブール値に変換して指定
        is_higher_better: isHigherBetterValue // スネークケース版も同時に更新
      });
    }
  };

  // パラメータヘルプテキストを生成
  const renderParameterHelp = () => {
    if (selectedMetricTypeInfo?.parameters) {
      return (
        <Box mt={1}>
          <Typography variant="subtitle2">利用可能なパラメータ:</Typography>
          <ul>
            {Object.entries(selectedMetricTypeInfo.parameters).map(([paramName, paramInfo]) => (
              <li key={paramName}>
                <code>{paramName}</code>
                {paramInfo.description && `: ${paramInfo.description}`}
                {paramInfo.default !== undefined && ` (デフォルト: ${JSON.stringify(paramInfo.default)})`}
                {paramInfo.required && ' (必須)'}
              </li>
            ))}
          </ul>
        </Box>
      );
    }
    return (
      <Box mt={1}>
        <Typography variant="subtitle2">利用可能なパラメータ例:</Typography>
        <ul>
          <li><code>exact_match</code>: <code>&#123;"ignore_case": true, "ignore_whitespace": true&#125;</code></li>
          <li><code>exact_match_figure</code>: <code>&#123;"ignore_case": true, "ignore_table_separators": true, "normalize_numbers": true&#125;</code></li>
          <li><code>bleu</code>: <code>&#123;"weights": [0.25, 0.25, 0.25, 0.25]&#125;</code></li>
          <li><code>char_f1</code>: <code>&#123;"beta": 1.0&#125;</code></li>
        </ul>
        各評価指標は異なるパラメータをサポートしています。
      </Box>
    );
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
            <FormControl fullWidth required error={!!errors.type}>
              <InputLabel>タイプ</InputLabel>
              <Select
                name="type"
                value={formData.type}
                onChange={handleChange}
                label="タイプ"
                disabled={isLoadingMetricTypes}
              >
                {isLoadingMetricTypes && (
                  <MenuItem value="" disabled>読み込み中...</MenuItem>
                )}
                {metricTypes && metricTypes.map((metricType) => (
                  <MenuItem key={metricType.name} value={metricType.name}>
                    {metricType.name}
                  </MenuItem>
                ))}
                {!isLoadingMetricTypes && (!metricTypes || metricTypes.length === 0) && (
                  <MenuItem value="custom">カスタム (Custom)</MenuItem>
                )}
              </Select>
              {errors.type && <FormHelperText>{errors.type}</FormHelperText>}
            </FormControl>
            {metricTypesError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                メトリックタイプの読み込みに失敗しました。デフォルトのタイプを使用します。
              </Alert>
            )}
            {selectedMetricTypeInfo?.description && (
              <FormHelperText>
                {selectedMetricTypeInfo.description}
              </FormHelperText>
            )}
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
                  checked={!!formData.isHigherBetter}
                  onChange={(e) => {
                    const newValue = !!e.target.checked;
                    console.log(`Switch changed from ${formData.isHigherBetter} to ${newValue} (${typeof newValue})`);
                    setFormData({
                      ...formData,
                      isHigherBetter: newValue,
                      is_higher_better: newValue // スネークケース版も同時に更新
                    });
                  }}
                  color="primary"
                />
              }
              label="値が高いほど良い"
            />
            <FormHelperText>
              この評価指標は値が高いほど良いパフォーマンスを示す場合はオン、低いほど良い場合はオフにしてください
              （現在の値: {!!formData.isHigherBetter ? "高いほど良い" : "低いほど良い"}）
            </FormHelperText>
            
            {/* デバッグ情報 */}
            <div style={{ marginTop: '8px', padding: '4px', backgroundColor: '#f5f5f5', fontSize: '10px' }}>
              値が高いほど良い: {String(formData.isHigherBetter)} (type: {typeof formData.isHigherBetter})<br />
              Switch checked: {String(!!formData.isHigherBetter)}
            </div>
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
              helperText={errors.parameters || '評価指標のパラメータをJSON形式で入力（例: {"threshold": 0.5, "ignore_case": true}）'}
              InputProps={{
                sx: { fontFamily: 'monospace' }
              }}
            />
            <FormHelperText>
              {renderParameterHelp()}
            </FormHelperText>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>キャンセル</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={isSubmitting || isLoadingMetricTypes}
          startIcon={isSubmitting ? <CircularProgress size={20} /> : null}
        >
          {initialData ? '更新' : '追加'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MetricFormDialog;
