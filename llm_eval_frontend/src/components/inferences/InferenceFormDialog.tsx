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
  FormHelperText,
  SelectChangeEvent,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Slider,
  Stack,
  Chip
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SettingsIcon from '@mui/icons-material/Settings';
import { InferenceFormData } from '../../types/inference';
import { Dataset } from '../../types/dataset';
import { Provider, Model } from '../../types/provider';

interface InferenceFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: InferenceFormData) => void;
  initialData?: InferenceFormData;
  isSubmitting: boolean;
  datasets: Dataset[];
  providers: Provider[];
  models: Model[];
}

/**
 * 推論作成用のフォームダイアログ
 * 評価API (/api/evaluation/run) と連携
 */
const InferenceFormDialog: React.FC<InferenceFormDialogProps> = ({
  open,
  onClose,
  onSubmit,
  initialData,
  isSubmitting,
  datasets,
  providers,
  models
}) => {
  // デフォルト値の設定
  const defaultData: InferenceFormData = {
    name: '',
    description: '',
    datasetId: '',
    providerId: '',
    modelId: '',
    numSamples: 100,     // デフォルト: 100
    nShots: 0,          // デフォルト: 0
    maxTokens: 512,      // デフォルト: 512
    temperature: 0.7,    // デフォルト: 0.7
    topP: 1.0            // デフォルト: 1.0
  };

  // フォームの状態
  const [formData, setFormData] = useState<InferenceFormData>(initialData || defaultData);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [expandedSettings, setExpandedSettings] = useState<boolean>(false);

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

  // 入力値の変更処理（テキストフィールド、セレクトボックス）
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | { name?: string; value: unknown }> | SelectChangeEvent) => {
    const { name, value } = e.target;
    if (name) {
      console.log(`Changing ${name} to:`, value); // デバッグ用
      
      // 更新前のフォームデータをログ出力
      console.log('Before update:', formData);
      
      setFormData(prev => {
        const newData = {
          ...prev,
          [name]: value
        };
        // 更新後のフォームデータをログ出力
        console.log('After update:', newData);
        return newData;
      });
      
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

  // 数値入力の変更処理
  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const numValue = parseFloat(value);
    
    if (!isNaN(numValue)) {
      setFormData(prev => ({
        ...prev,
        [name]: numValue
      }));
    }
  };

  // スライダーの変更処理
  const handleSliderChange = (name: string) => (_event: Event, newValue: number | number[]) => {
    setFormData(prev => ({
      ...prev,
      [name]: newValue
    }));
  };

  // バリデーション
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = '名前は必須です';
    }
    
    if (!formData.datasetId) {
      newErrors.datasetId = 'データセットは必須です';
    }
    
    if (!formData.providerId) {
      newErrors.providerId = 'プロバイダは必須です';
    }
    
    if (!formData.modelId) {
      newErrors.modelId = 'モデルは必須です';
    }

    // 数値パラメータのバリデーション
    if (formData.numSamples !== undefined && (formData.numSamples < 1 || formData.numSamples > 1000)) {
      newErrors.numSamples = 'サンプル数は1から1000の間で指定してください';
    }

    if (formData.nShots !== undefined && (formData.nShots < 0 || formData.nShots > 10)) {
      newErrors.nShots = 'Few-shot数は0から10の間で指定してください';
    }

    if (formData.maxTokens !== undefined && (formData.maxTokens < 1 || formData.maxTokens > 4096)) {
      newErrors.maxTokens = '最大トークン数は1から4096の間で指定してください';
    }

    if (formData.temperature !== undefined && (formData.temperature < 0 || formData.temperature > 2)) {
      newErrors.temperature = '温度パラメータは0から2の間で指定してください';
    }

    if (formData.topP !== undefined && (formData.topP < 0 || formData.topP > 1)) {
      newErrors.topP = 'Top-pは0から1の間で指定してください';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // フォーム送信
  const handleSubmit = () => {
    if (validate()) {
      // データセットIDから名前とタイプを抽出（"name__type"形式）
      let datasetName = formData.datasetId;
      let datasetType = '';
      
      if (formData.datasetId && formData.datasetId.includes('__')) {
        const parts = formData.datasetId.split('__');
        datasetName = parts[0];
        datasetType = parts[1];
      }
      
      // APIによる推論作成のためにデータを準備
      const processedData = {
        ...formData,
        // ユーザーが指定したサンプル数をそのまま使用
        numSamples: formData.numSamples,
        // 名前とタイプを分離
        datasetId: datasetName,
        datasetType: datasetType, // 新しいフィールド
        // スネークケース形式のフィールド名を追加（バックエンドAPI用）
        dataset_id: datasetName,
        dataset_type: datasetType, // 新しいフィールド
        provider_id: formData.providerId,
        model_id: formData.modelId,
        num_samples: formData.numSamples,
        n_shots: formData.nShots,
        max_tokens: formData.maxTokens,
        top_p: formData.topP
      };
      
      // 詳細なログを出力
      console.log('フォーム送信データ (元):', formData);
      console.log('フォーム送信データ (処理後):', processedData);
      console.log('データセット名:', processedData.datasetId);
      console.log('データセットタイプ:', processedData.datasetType);
      console.log('サンプル数:', processedData.numSamples);
      
      // 処理済みデータを送信
      onSubmit(processedData);
    }
  };

  // 選択されたプロバイダに基づいてフィルタリングされたモデルリスト
  const filteredModels = models.filter(model => {
    // プロバイダが選択されていない場合はすべてのモデルを表示
    if (!formData.providerId) return true;
    // モデルのプロバイダIDと選択されたプロバイダIDが一致するモデルのみ表示
    return model.providerId === formData.providerId;
  });

  // 選択されたプロバイダとモデル情報
  const selectedProvider = providers.find(p => p.id === formData.providerId);
  const selectedModel = models.find(m => m.id === formData.modelId);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        推論の作成
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <TextField
              name="name"
              label="推論名"
              fullWidth
              value={formData.name}
              onChange={handleChange}
              error={!!errors.name}
              helperText={errors.name}
              required
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
              helperText="推論の説明（オプション）"
            />
          </Grid>
          
          <Grid item xs={12}>
            <FormControl fullWidth required error={!!errors.datasetId}>
              <InputLabel id="dataset-select-label">データセット</InputLabel>
              <Select
                labelId="dataset-select-label"
                id="dataset-select"
                name="datasetId"
                value={formData.datasetId || ''}
                onChange={(e) => {
                  // 詳細なデバッグ情報
                  console.log('Dataset selection event type:', e.type);
                  console.log('Dataset selection raw value:', e.target.value);
                  
                  // MUIのSelectChangeEventからstring型の値を直接取得
                  const selectedValue = String(e.target.value);
                  console.log('Dataset selection converted value:', selectedValue);
                  
                  // 直接フォームデータを更新
                  setFormData(prevData => {
                    const newData = {
                      ...prevData,
                      datasetId: selectedValue
                    };
                    console.log('Updated form data directly:', newData);
                    return newData;
                  });
                  
                  // エラーをクリア
                  if (errors.datasetId) {
                    setErrors(prev => {
                      const newErrors = { ...prev };
                      delete newErrors.datasetId;
                      return newErrors;
                    });
                  }
                }}
                label="データセット"
              >
                {datasets.map((dataset) => (
                  <MenuItem 
                    key={dataset.id || dataset.name} 
                    value={`${dataset.name}__${dataset.type}`} // 名前とタイプを組み合わせた値を使用
                  >
                    {dataset.name} ({dataset.type || ''})
                    {/* デバッグ情報は削除 */}
                  </MenuItem>
                ))}
              </Select>
              {errors.datasetId && <FormHelperText>{errors.datasetId}</FormHelperText>}
            </FormControl>
          </Grid>
          
          <Grid item xs={12}>
            <FormControl fullWidth required error={!!errors.providerId}>
              <InputLabel id="provider-select-label">プロバイダ</InputLabel>
              <Select
                labelId="provider-select-label"
                id="provider-select"
                name="providerId"
                value={formData.providerId || ''}
                onChange={handleChange}
                label="プロバイダ"
              >
                {providers.map((provider) => (
                  <MenuItem key={provider.id} value={provider.id}>
                    {provider.name} ({provider.type || 'unknown'})
                  </MenuItem>
                ))}
              </Select>
              {errors.providerId && <FormHelperText>{errors.providerId}</FormHelperText>}
            </FormControl>
          </Grid>
          
          <Grid item xs={12}>
            <FormControl fullWidth required error={!!errors.modelId}>
              <InputLabel id="model-select-label">モデル</InputLabel>
              <Select
                labelId="model-select-label"
                id="model-select"
                name="modelId"
                value={formData.modelId || ''}
                onChange={handleChange}
                label="モデル"
                disabled={!formData.providerId}
              >
                {filteredModels.map((model) => (
                  <MenuItem key={model.id} value={model.id}>
                    {model.displayName}
                  </MenuItem>
                ))}
              </Select>
              {errors.modelId && <FormHelperText>{errors.modelId}</FormHelperText>}
              {!formData.providerId && <FormHelperText>先にプロバイダを選択してください</FormHelperText>}
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <Accordion 
              expanded={expandedSettings} 
              onChange={() => setExpandedSettings(!expandedSettings)}
              sx={{ mt: 2 }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <SettingsIcon fontSize="small" />
                  <Typography>詳細設定</Typography>
                  <Chip 
                    label={`サンプル数: ${formData.numSamples}`} 
                    size="small" 
                    color="primary" 
                    variant="outlined"
                  />
                  <Chip 
                    label={`Few-shot: ${formData.nShots}`} 
                    size="small" 
                    color="primary" 
                    variant="outlined"
                  />
                </Stack>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography gutterBottom>
                      サンプル数: {formData.numSamples}
                    </Typography>
                    <Slider
                      value={formData.numSamples}
                      onChange={handleSliderChange('numSamples')}
                      min={1}
                      max={1000}
                      step={10}
                      marks={[
                        { value: 1, label: '1' },
                        { value: 100, label: '100' },
                        { value: 500, label: '500' },
                        { value: 1000, label: '1000' }
                      ]}
                    />
                    <TextField
                      label="サンプル数"
                      type="number"
                      name="numSamples"
                      value={formData.numSamples}
                      onChange={handleNumberChange}
                      InputProps={{
                        inputProps: {
                          min: 1,
                          max: 1000
                        }
                      }}
                      size="small"
                      fullWidth
                      margin="normal"
                      error={!!errors.numSamples}
                      helperText={errors.numSamples}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography gutterBottom>
                      Few-shot数: {formData.nShots}
                    </Typography>
                    <Slider
                      value={formData.nShots}
                      onChange={handleSliderChange('nShots')}
                      min={0}
                      max={10}
                      step={1}
                      marks={[
                        { value: 0, label: '0' },
                        { value: 3, label: '3' },
                        { value: 5, label: '5' },
                        { value: 10, label: '10' }
                      ]}
                    />
                    <TextField
                      label="Few-shot数"
                      type="number"
                      name="nShots"
                      value={formData.nShots}
                      onChange={handleNumberChange}
                      InputProps={{
                        inputProps: {
                          min: 0,
                          max: 10
                        }
                      }}
                      size="small"
                      fullWidth
                      margin="normal"
                      error={!!errors.nShots}
                      helperText={errors.nShots}
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Typography gutterBottom>
                      最大トークン数: {formData.maxTokens}
                    </Typography>
                    <Slider
                      value={formData.maxTokens}
                      onChange={handleSliderChange('maxTokens')}
                      min={1}
                      max={4096}
                      step={128}
                      marks={[
                        { value: 512, label: '512' },
                        { value: 2048, label: '2048' },
                        { value: 4096, label: '4096' }
                      ]}
                    />
                    <TextField
                      label="最大トークン数"
                      type="number"
                      name="maxTokens"
                      value={formData.maxTokens}
                      onChange={handleNumberChange}
                      InputProps={{
                        inputProps: {
                          min: 1,
                          max: 4096
                        }
                      }}
                      size="small"
                      fullWidth
                      margin="normal"
                      error={!!errors.maxTokens}
                      helperText={errors.maxTokens}
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Typography gutterBottom>
                      温度: {formData.temperature}
                    </Typography>
                    <Slider
                      value={formData.temperature}
                      onChange={handleSliderChange('temperature')}
                      min={0}
                      max={2}
                      step={0.1}
                      marks={[
                        { value: 0, label: '0' },
                        { value: 0.7, label: '0.7' },
                        { value: 1, label: '1' },
                        { value: 2, label: '2' }
                      ]}
                    />
                    <TextField
                      label="温度"
                      type="number"
                      name="temperature"
                      value={formData.temperature}
                      onChange={handleNumberChange}
                      InputProps={{
                        inputProps: {
                          min: 0,
                          max: 2,
                          step: 0.1
                        }
                      }}
                      size="small"
                      fullWidth
                      margin="normal"
                      error={!!errors.temperature}
                      helperText={errors.temperature}
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Typography gutterBottom>
                      Top-p: {formData.topP}
                    </Typography>
                    <Slider
                      value={formData.topP}
                      onChange={handleSliderChange('topP')}
                      min={0}
                      max={1}
                      step={0.05}
                      marks={[
                        { value: 0, label: '0' },
                        { value: 0.5, label: '0.5' },
                        { value: 1, label: '1' }
                      ]}
                    />
                    <TextField
                      label="Top-p"
                      type="number"
                      name="topP"
                      value={formData.topP}
                      onChange={handleNumberChange}
                      InputProps={{
                        inputProps: {
                          min: 0,
                          max: 1,
                          step: 0.05
                        }
                      }}
                      size="small"
                      fullWidth
                      margin="normal"
                      error={!!errors.topP}
                      helperText={errors.topP}
                    />
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
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
          作成
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default InferenceFormDialog;
