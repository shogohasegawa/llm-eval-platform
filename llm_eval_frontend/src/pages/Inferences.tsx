import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Grid, 
  Paper, 
  CircularProgress,
  Alert,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Stack
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { useQueryClient } from '@tanstack/react-query';
import { useInferences, useCreateInference, useDeleteInference, useRunInference, useStopInference } from '../hooks/useInferences';
import { useDatasets } from '../hooks/useDatasets';
import { useProviders, useModels } from '../hooks/useProviders';
import { Inference, InferenceFormData, InferenceFilterOptions } from '../types/inference';
import { useAppContext } from '../contexts/AppContext';
import InferenceCard from '../components/inferences/InferenceCard';
import InferenceFormDialog from '../components/inferences/InferenceFormDialog';
import { useNavigate } from 'react-router-dom';
import { inferencesApi } from '../api/inferences';

/**
 * 推論管理ページ
 */
const Inferences: React.FC = () => {
  const navigate = useNavigate();
  
  // コンテキストから状態を取得
  const { setError } = useAppContext();
  const queryClient = useQueryClient();
  
  // フィルター状態
  const [filters, setFilters] = useState<InferenceFilterOptions>({});
  
  // ダイアログの状態
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  
  // 推論データの取得
  const { 
    data: rawInferences, 
    isLoading: isLoadingInferences, 
    isError: isErrorInferences, 
    error: inferencesError,
    refetch: refetchInferences // 明示的に再取得するための関数
  } = useInferences(filters);
  
  // 表示用に整形した推論データ
  const [inferences, setInferences] = useState<Inference[]>([]);
  
  // データセットデータの取得
  const {
    data: datasets,
    isLoading: isLoadingDatasets,
    isError: isErrorDatasets,
    error: datasetsError
  } = useDatasets();
  
  // プロバイダデータの取得
  const {
    data: providers,
    isLoading: isLoadingProviders,
    isError: isErrorProviders,
    error: providersError
  } = useProviders();
  
  // モデルデータの取得
  const {
    data: modelsData,
    isLoading: isLoadingModels,
    isError: isErrorModels,
    error: modelsError
  } = useModels();
  
  // ミューテーションフック
  const createInference = useCreateInference();
  const deleteInference = useDeleteInference();
  const runInference = useRunInference('');
  const stopInference = useStopInference('');
  
  // モデルリストの取得と整形
  const [models, setModels] = useState<any[]>([]);
  
  // プロバイダとモデルを連携
  useEffect(() => {
    if (providers && modelsData) {
      console.log('Providers:', providers);
      console.log('Models:', modelsData);
      
      // 各モデルにproviderId情報が既に含まれていることを確認
      const processedModels = modelsData.map(model => {
        // 対応するプロバイダ情報を取得
        const provider = providers.find(p => p.id === model.providerId);
        return {
          ...model,
          providerName: provider?.name || 'Unknown',
          providerType: provider?.type || 'unknown'
        };
      });
      
      setModels(processedModels);
      console.log('Processed models:', processedModels);
    }
  }, [providers, modelsData]);
  
  // 推論データを人間が読みやすい名前で強化
  useEffect(() => {
    if (rawInferences && providers && models) {
      console.log('推論データにモデル・プロバイダ情報を追加中...');
      console.log('- 推論データ:', rawInferences?.length || 0, '件');
      console.log('- プロバイダデータ:', providers?.length || 0, '件');
      console.log('- モデルデータ:', models?.length || 0, '件');
      
      const enrichedInferences = rawInferences.map(inference => {
        // 推論データのモデルIDとプロバイダID
        const inferenceModelId = inference.modelId;
        const inferenceProviderId = inference.providerId;
        
        console.log(`推論 "${inference.name}" (ID: ${inference.id}):`);
        console.log(`- 元のモデルID: ${inferenceModelId}`);
        console.log(`- 元のプロバイダID: ${inferenceProviderId}`);
        
        // モデル名の検索
        const model = models.find(m => m.id === inferenceModelId);
        if (model) {
          console.log(`- 一致するモデル検索成功:`, model.name);
        } else {
          console.log(`- モデル検索失敗: ID ${inferenceModelId} に一致するモデルがありません`);
        }
        
        // プロバイダ名の検索
        const provider = providers.find(p => p.id === inferenceProviderId);
        if (provider) {
          console.log(`- 一致するプロバイダ検索成功:`, provider.name);
        } else {
          console.log(`- プロバイダ検索失敗: ID ${inferenceProviderId} に一致するプロバイダがありません`);
        }
        
        // 強化されたデータを返す
        return {
          ...inference,
          modelName: model?.name || model?.displayName || undefined,
          providerName: provider?.name || undefined,
          providerType: provider?.type || undefined
        };
      });
      
      console.log('強化後の推論データ:', enrichedInferences);
      setInferences(enrichedInferences);
    } else if (rawInferences) {
      // モデルやプロバイダデータがまだ読み込まれていない場合は、そのまま設定
      console.log('モデル・プロバイダデータがロードされていないため、生の推論データを使用します');
      setInferences(rawInferences);
    }
  }, [rawInferences, providers, models]);
  
  // データの取得状況をログに出力
  console.log('Datasets data:', datasets);
  console.log('Providers data:', providers);
  console.log('Models data:', modelsData);
  console.log('Inferences data:', inferences);
  
  // データ取得状況の確認
  console.log('データ取得状況:',
    datasets?.length ? `データセット: ${datasets.length}件取得済み` : 'データセット: 未取得',
    providers?.length ? `プロバイダ: ${providers.length}件取得済み` : 'プロバイダ: 未取得',
    models?.length ? `モデル: ${models.length}件取得済み` : 'モデル: 未取得'
  );
  
  // 初回ロード時に推論一覧を取得
  useEffect(() => {
    // コンポーネントマウント時に一度だけ実行
    console.log('推論一覧を初期ロードします...');
    refetchInferences();
    
    // 30秒ごとに自動リフレッシュ（進行中の推論に関わらず）
    const refreshIntervalId = setInterval(() => {
      console.log('定期リフレッシュ: 推論一覧を更新します...');
      refetchInferences();
    }, 30000);
    
    return () => {
      console.log('定期リフレッシュを停止します');
      clearInterval(refreshIntervalId);
    };
  }, [refetchInferences]);

  // 進行中の推論があれば、より頻繁に更新を行う
  useEffect(() => {
    // 進行中の推論があるかチェック
    const hasRunningInference = inferences?.some(inf => inf.status === 'running' || inf.status === 'pending');
    
    if (hasRunningInference) {
      console.log('進行中の推論があります。頻繁な更新を開始します...');
      
      // 各推論の状態をログ出力（デバッグ用）
      inferences?.forEach(inf => {
        if (inf.status === 'running' || inf.status === 'pending') {
          console.log(`推論ID: ${inf.id}, 名前: ${inf.name}, 状態: ${inf.status}, 進捗: ${inf.progress}%`);
        }
      });
      
      // 5秒ごとに自動更新（進行中推論がある場合はより頻繁に）
      const intervalId = setInterval(() => {
        console.log('高頻度更新: 進行中の推論の状態を確認します...');
        refetchInferences();
      }, 5000);
      
      // クリーンアップ関数
      return () => {
        console.log('高頻度更新を停止します');
        clearInterval(intervalId);
      };
    }
  }, [inferences, refetchInferences]);
  
  // エラーハンドリング
  if (inferencesError) {
    console.error('推論取得エラー:', inferencesError);
    setError(`推論の取得に失敗しました: ${inferencesError.message}`);
  }
  
  if (datasetsError) {
    console.error('データセット取得エラー:', datasetsError);
    setError(`データセットの取得に失敗しました: ${datasetsError.message}`);
  }
  
  if (providersError) {
    console.error('プロバイダ取得エラー:', providersError);
    setError(`プロバイダの取得に失敗しました: ${providersError.message}`);
  }
  
  if (modelsError) {
    console.error('モデル取得エラー:', modelsError);
    setError(`モデルの取得に失敗しました: ${modelsError.message}`);
  }
  
  // 推論の作成ダイアログを開く
  const handleOpenFormDialog = () => {
    setFormDialogOpen(true);
  };
  
  // 推論の作成ダイアログを閉じる
  const handleCloseFormDialog = () => {
    setFormDialogOpen(false);
  };
  
  // 推論の作成を実行
  const handleSubmitInference = async (data: InferenceFormData) => {
    try {
      console.log('Original inference data from form:', data);
      
      // データセットをより正確に送信（スネークケースとキャメルケースの両方）
      const inferenceData = {
        ...data,
        // そのままスネークケースでも同じデータを設定
        dataset_id: data.datasetId,
        provider_id: data.providerId,
        model_id: data.modelId,
        // サンプル数はフォームで指定された値を使用
        numSamples: data.numSamples || 100,  // デフォルト100
        num_samples: data.numSamples || 100, // デフォルト100
        // 必要なフィールドもすべて設定
        n_shots: data.nShots || 0,
        max_tokens: data.maxTokens || 512,
        temperature: data.temperature || 0.7,
        top_p: data.topP || 1.0,
      };
      console.log('Prepared inference data for API call:', inferenceData);
      
      // ネットワークリクエストを明示的にロギング
      console.log('Sending inference request to API...');
      
      try {
        // APIクライアントではなく直接フェッチを使用
        const response = await fetch('/api/v1/inferences', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(inferenceData),
        });
        
        console.log('Raw API response status:', response.status);
        
        if (!response.ok) {
          const errorData = await response.text();
          console.error('API error response:', errorData);
          throw new Error(`API error: ${response.status} ${response.statusText}\n${errorData}`);
        }
        
        const result = await response.json();
        console.log('API response data:', result);
        
        // 推論IDの抽出（レスポンス形式によって変わる可能性あり）
        const inferenceId = result.id || (result.inference && result.inference.id);
        console.log('Created inference ID:', inferenceId);
        
        // 正常処理を続行
        handleCloseFormDialog();
        
        // 成功メッセージを表示
        // Contextのimplementaionによってはエラーが起きる可能性があるため条件付きで実行
        try {
          // @ts-ignore - AppContextのsetErrorが第2引数をサポートしている場合
          setError(`推論が正常に作成されました: ${result.name || '名称なし'}`, "success");
        } catch (err) {
          console.log('推論が正常に作成されました:', result.name || '名称なし');
          // フォールバック：通常のエラー表示は使わない
        }
        
        // 推論一覧を明示的に再取得 - まず即時再取得
        console.log('Refreshing inferences list immediately...');
        await refetchInferences();
        
        // 推論作成後の監視（より安定したアプローチ）
        let initialPollingComplete = false;
        let extendedPollingStarted = false;
        let initialCheckCount = 0;
        let extendedCheckCount = 0;
        const MAX_INITIAL_CHECKS = 20; // 最初の高頻度チェック回数（20秒）
        const MAX_EXTENDED_CHECKS = 180; // 拡張チェック回数（30分 = 180回 × 10秒）
        
        // 1秒ごとに最初のチェック（高頻度フェーズ）
        console.log('Starting initial high-frequency polling...');
        const initialPoller = setInterval(async () => {
          try {
            initialCheckCount++;
            console.log(`Initial poll ${initialCheckCount}/${MAX_INITIAL_CHECKS}...`);
            
            // 推論リストを再取得
            await refetchInferences();
            
            // 完了しているか確認
            const updatedInferences = await inferencesApi.getInferences();
            const targetInference = updatedInferences.find(inf => inf.id === inferenceId);
            
            // 推論オブジェクトが見つかり、状態が確定している場合
            if (targetInference && (targetInference.status === 'completed' || targetInference.status === 'failed')) {
              console.log('Inference completed or failed during initial polling:', targetInference.status);
              clearInterval(initialPoller);
              initialPollingComplete = true;
              return;
            }
            
            // 最大チェック回数に達した場合は拡張ポーリングに切り替え
            if (initialCheckCount >= MAX_INITIAL_CHECKS && !initialPollingComplete) {
              console.log('Max initial checks reached, switching to extended polling...');
              clearInterval(initialPoller);
              initialPollingComplete = true;
              extendedPollingStarted = true;
              
              // 拡張ポーリングを開始（10秒ごと）
              const extendedPoller = setInterval(async () => {
                try {
                  extendedCheckCount++;
                  console.log(`Extended poll ${extendedCheckCount}/${MAX_EXTENDED_CHECKS}...`);
                  
                  // 推論リストを再取得
                  await refetchInferences();
                  
                  // 完了しているかもう一度確認
                  const latestInferences = await inferencesApi.getInferences();
                  const latestTarget = latestInferences.find(inf => inf.id === inferenceId);
                  
                  // 推論オブジェクトが見つかり、状態が確定している場合
                  if (latestTarget && (latestTarget.status === 'completed' || latestTarget.status === 'failed')) {
                    console.log('Inference completed or failed during extended polling:', latestTarget.status);
                    clearInterval(extendedPoller);
                    return;
                  }
                  
                  // 最大チェック回数に達した場合は終了
                  if (extendedCheckCount >= MAX_EXTENDED_CHECKS) {
                    console.log('Max extended checks reached, stopping polling...');
                    clearInterval(extendedPoller);
                  }
                } catch (pollingError) {
                  console.error('Error during extended polling:', pollingError);
                  // エラーが発生しても継続（ポーリング自体は停止しない）
                }
              }, 10000); // 10秒間隔
            }
          } catch (pollingError) {
            console.error('Error during initial polling:', pollingError);
            // エラーが発生しても継続（ポーリング自体は停止しない）
          }
        }, 1000); // 1秒間隔
      } catch (fetchError) {
        throw new Error(`API通信エラー: ${fetchError.message}`);
      }
    } catch (err) {
      if (err instanceof Error) {
        console.error('Error creating inference:', err);
        setError(`推論の作成に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 推論の削除を実行
  const handleDeleteInference = async (id: string) => {
    try {
      await deleteInference.mutateAsync(id);
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の削除に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 推論の実行を開始
  const handleRunInference = async (inference: Inference) => {
    try {
      await runInference.mutateAsync(inference.id);
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の実行に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 推論の実行を停止
  const handleStopInference = async (inference: Inference) => {
    try {
      await stopInference.mutateAsync(inference.id);
    } catch (err) {
      if (err instanceof Error) {
        setError(`推論の停止に失敗しました: ${err.message}`);
      }
    }
  };
  
  // 推論の詳細を表示
  const handleViewInference = (inference: Inference) => {
    navigate(`/inferences/${inference.id}`);
  };
  
  // フィルターの変更処理
  const handleFilterChange = (e: SelectChangeEvent<string | number>) => {
    const { name, value } = e.target;
    if (name) {
      setFilters(prev => ({
        ...prev,
        [name]: value === 'all' ? undefined : value
      }));
    }
  };
  
  // ローディング中
  const isLoading = isLoadingInferences || isLoadingDatasets || isLoadingProviders || isLoadingModels;
  
  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          推論管理
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenFormDialog}
          disabled={!datasets?.length || !providers?.length || !models?.length}
        >
          推論を作成
        </Button>
      </Box>
      
      <Divider sx={{ mb: 3 }} />
      
      {/* フィルター */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>データセット</InputLabel>
              <Select
                name="datasetId"
                value={filters.datasetId || 'all'}
                onChange={handleFilterChange}
                label="データセット"
              >
                <MenuItem value="all">すべて</MenuItem>
                {datasets?.map((dataset) => (
                  <MenuItem key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>プロバイダ</InputLabel>
              <Select
                name="providerId"
                value={filters.providerId || 'all'}
                onChange={handleFilterChange}
                label="プロバイダ"
              >
                <MenuItem value="all">すべて</MenuItem>
                {providers?.map((provider) => (
                  <MenuItem key={provider.id} value={provider.id}>
                    {provider.name} ({provider.type || 'unknown'})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>ステータス</InputLabel>
              <Select
                name="status"
                value={filters.status || 'all'}
                onChange={handleFilterChange}
                label="ステータス"
              >
                <MenuItem value="all">すべて</MenuItem>
                <MenuItem value="pending">待機中</MenuItem>
                <MenuItem value="running">実行中</MenuItem>
                <MenuItem value="completed">完了</MenuItem>
                <MenuItem value="failed">失敗</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>
      
      {isLoading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : isErrorInferences ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          推論の取得中にエラーが発生しました。
        </Alert>
      ) : inferences && inferences.length > 0 ? (
        <Box>
          <Stack spacing={1}>
            {/* 新しい推論を上に表示するためにreverseする */}
            {[...inferences]
              .sort((a, b) => {
                // 作成日時の新しい順にソート
                return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
              })
              .map((inference) => (
                <InferenceCard
                  key={inference.id}
                  inference={inference}
                  onRun={handleRunInference}
                  onStop={handleStopInference}
                  onDelete={handleDeleteInference}
                  onView={handleViewInference}
                />
              ))
            }
          </Stack>
        </Box>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            推論が登録されていません。「推論を作成」ボタンをクリックして最初の推論を作成してください。
          </Typography>
        </Paper>
      )}
      
      {/* 推論作成ダイアログ */}
      {formDialogOpen && datasets && providers && (
        <InferenceFormDialog
          open={formDialogOpen}
          onClose={handleCloseFormDialog}
          onSubmit={handleSubmitInference}
          isSubmitting={createInference.isPending}
          datasets={datasets}
          providers={providers}
          models={models}
        />
      )}
    </Box>
  );
};

export default Inferences;
