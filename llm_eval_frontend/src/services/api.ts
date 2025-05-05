import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import { providersRepository } from '../db/providers.repository';
import { datasetsRepository } from '../db/datasets.repository';
import { inferencesRepository } from '../db/inferences.repository';
import { metricsRepository } from '../db/metrics.repository';

// Express アプリケーションの作成
const app = express();

// ミドルウェアの設定
app.use(cors());
app.use(bodyParser.json({ limit: '10mb' }));

// --------------------------------------------------
// プロバイダ関連エンドポイント
// --------------------------------------------------

// プロバイダ一覧を取得
app.get('/api/providers', (req, res) => {
  try {
    const providers = providersRepository.getProviders();
    res.json(providers);
  } catch (error) {
    console.error('Error fetching providers:', error);
    res.status(500).json({ error: 'Failed to fetch providers' });
  }
});

// 特定のプロバイダを取得
app.get('/api/providers/:id', (req, res) => {
  try {
    const provider = providersRepository.getProvider(req.params.id);
    if (!provider) {
      return res.status(404).json({ error: 'Provider not found' });
    }
    res.json(provider);
  } catch (error) {
    console.error(`Error fetching provider ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to fetch provider' });
  }
});

// プロバイダを作成
app.post('/api/providers', (req, res) => {
  try {
    const provider = providersRepository.createProvider(req.body);
    res.status(201).json(provider);
  } catch (error) {
    console.error('Error creating provider:', error);
    res.status(500).json({ error: 'Failed to create provider' });
  }
});

// プロバイダを更新
app.put('/api/providers/:id', (req, res) => {
  try {
    const provider = providersRepository.updateProvider(req.params.id, req.body);
    if (!provider) {
      return res.status(404).json({ error: 'Provider not found' });
    }
    res.json(provider);
  } catch (error) {
    console.error(`Error updating provider ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to update provider' });
  }
});

// プロバイダを削除
app.delete('/api/providers/:id', (req, res) => {
  try {
    const success = providersRepository.deleteProvider(req.params.id);
    if (!success) {
      return res.status(404).json({ error: 'Provider not found' });
    }
    res.status(204).send();
  } catch (error) {
    console.error(`Error deleting provider ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to delete provider' });
  }
});

// 全モデル一覧を取得
app.get('/api/models', (req, res) => {
  try {
    const allModels = [];
    const providers = providersRepository.getProviders();
    
    for (const provider of providers) {
      const models = providersRepository.getProviderModels(provider.id);
      allModels.push(...models);
    }
    
    res.json(allModels);
  } catch (error) {
    console.error('Error fetching all models:', error);
    res.status(500).json({ error: 'Failed to fetch models' });
  }
});

// プロバイダのモデル一覧を取得
app.get('/api/providers/:id/models', (req, res) => {
  try {
    const models = providersRepository.getProviderModels(req.params.id);
    res.json(models);
  } catch (error) {
    console.error(`Error fetching models for provider ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to fetch models' });
  }
});

// 特定のモデルを取得
app.get('/api/models/:id', (req, res) => {
  try {
    const model = providersRepository.getModel(req.params.id);
    if (!model) {
      return res.status(404).json({ error: 'Model not found' });
    }
    res.json(model);
  } catch (error) {
    console.error(`Error fetching model ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to fetch model' });
  }
});

// モデルを作成
app.post('/api/models', (req, res) => {
  try {
    const model = providersRepository.createModel(req.body);
    res.status(201).json(model);
  } catch (error) {
    console.error('Error creating model:', error);
    res.status(500).json({ error: 'Failed to create model' });
  }
});

// モデルを更新
app.put('/api/models/:modelId', (req, res) => {
  try {
    const model = providersRepository.updateModel(req.params.modelId, req.body);
    if (!model) {
      return res.status(404).json({ error: 'Model not found' });
    }
    res.json(model);
  } catch (error) {
    console.error(`Error updating model ${req.params.modelId}:`, error);
    res.status(500).json({ error: 'Failed to update model' });
  }
});

// モデルを削除
app.delete('/api/models/:modelId', (req, res) => {
  try {
    const success = providersRepository.deleteModel(req.params.modelId);
    if (!success) {
      return res.status(404).json({ error: 'Model not found' });
    }
    res.status(204).send();
  } catch (error) {
    console.error(`Error deleting model ${req.params.modelId}:`, error);
    res.status(500).json({ error: 'Failed to delete model' });
  }
});

// プロバイダ検証エンドポイント（モック実装）
app.post('/api/providers/validate/:type', (req, res) => {
  try {
    const { type } = req.params;
    const { endpoint, apiKey } = req.body;
    
    // 検証は常に成功するモック実装
    const valid = providersRepository.validateProvider(type, endpoint, apiKey);
    
    if (valid) {
      res.json({ valid: true });
    } else {
      res.status(400).json({ valid: false, error: 'Invalid credentials' });
    }
  } catch (error) {
    console.error(`Error validating provider:`, error);
    res.status(500).json({ valid: false, error: 'Failed to validate provider' });
  }
});

// --------------------------------------------------
// データセット関連エンドポイント
// --------------------------------------------------

// データセット一覧を取得
app.get('/api/datasets', (req, res) => {
  try {
    const datasets = datasetsRepository.getDatasets();
    res.json(datasets);
  } catch (error) {
    console.error('Error fetching datasets:', error);
    res.status(500).json({ error: 'Failed to fetch datasets' });
  }
});

// 特定のデータセットを取得
app.get('/api/datasets/:id', (req, res) => {
  try {
    const dataset = datasetsRepository.getDataset(req.params.id);
    if (!dataset) {
      return res.status(404).json({ error: 'Dataset not found' });
    }
    res.json(dataset);
  } catch (error) {
    console.error(`Error fetching dataset ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to fetch dataset' });
  }
});

// データセットを作成
app.post('/api/datasets', (req, res) => {
  try {
    const dataset = datasetsRepository.createDataset(req.body);
    res.status(201).json(dataset);
  } catch (error) {
    console.error('Error creating dataset:', error);
    res.status(500).json({ error: 'Failed to create dataset' });
  }
});

// データセットを更新
app.put('/api/datasets/:id', (req, res) => {
  try {
    const dataset = datasetsRepository.updateDataset(req.params.id, req.body);
    if (!dataset) {
      return res.status(404).json({ error: 'Dataset not found' });
    }
    res.json(dataset);
  } catch (error) {
    console.error(`Error updating dataset ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to update dataset' });
  }
});

// データセットを削除
app.delete('/api/datasets/:id', (req, res) => {
  try {
    const success = datasetsRepository.deleteDataset(req.params.id);
    if (!success) {
      return res.status(404).json({ error: 'Dataset not found' });
    }
    res.status(204).send();
  } catch (error) {
    console.error(`Error deleting dataset ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to delete dataset' });
  }
});

// データセットアイテムを取得
app.get('/api/datasets/:id/items', (req, res) => {
  try {
    const items = datasetsRepository.getDatasetItems(req.params.id);
    res.json(items);
  } catch (error) {
    console.error(`Error fetching items for dataset ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to fetch dataset items' });
  }
});

// データセットアイテムを追加
app.post('/api/datasets/:id/items', (req, res) => {
  try {
    const item = datasetsRepository.addDatasetItem(req.params.id, req.body);
    res.status(201).json(item);
  } catch (error) {
    console.error(`Error adding item to dataset ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to add dataset item' });
  }
});

// データセットアイテムを更新
app.put('/api/datasets/:datasetId/items/:itemId', (req, res) => {
  try {
    const item = datasetsRepository.updateDatasetItem(req.params.datasetId, req.params.itemId, req.body);
    if (!item) {
      return res.status(404).json({ error: 'Dataset item not found' });
    }
    res.json(item);
  } catch (error) {
    console.error(`Error updating dataset item ${req.params.itemId}:`, error);
    res.status(500).json({ error: 'Failed to update dataset item' });
  }
});

// データセットアイテムを削除
app.delete('/api/datasets/:datasetId/items/:itemId', (req, res) => {
  try {
    const success = datasetsRepository.deleteDatasetItem(req.params.datasetId, req.params.itemId);
    if (!success) {
      return res.status(404).json({ error: 'Dataset item not found' });
    }
    res.status(204).send();
  } catch (error) {
    console.error(`Error deleting dataset item ${req.params.itemId}:`, error);
    res.status(500).json({ error: 'Failed to delete dataset item' });
  }
});

// データセットをインポート
app.post('/api/datasets/import', (req, res) => {
  try {
    const jsonData = JSON.stringify(req.body);
    const dataset = datasetsRepository.importFromJson(jsonData);
    if (!dataset) {
      return res.status(400).json({ error: 'Invalid dataset format' });
    }
    res.status(201).json(dataset);
  } catch (error) {
    console.error('Error importing dataset:', error);
    res.status(500).json({ error: 'Failed to import dataset' });
  }
});

// データセットをエクスポート
app.get('/api/datasets/:id/export', (req, res) => {
  try {
    const jsonData = datasetsRepository.exportToJson(req.params.id);
    if (!jsonData) {
      return res.status(404).json({ error: 'Dataset not found' });
    }
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="dataset-${req.params.id}.json"`);
    res.send(jsonData);
  } catch (error) {
    console.error(`Error exporting dataset ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to export dataset' });
  }
});

// --------------------------------------------------
// 推論関連エンドポイント
// --------------------------------------------------

// 推論一覧を取得
app.get('/api/inferences', (req, res) => {
  try {
    const filters = {
      datasetId: req.query.datasetId as string,
      providerId: req.query.providerId as string,
      modelId: req.query.modelId as string,
      status: req.query.status as any
    };
    
    const inferences = inferencesRepository.getInferences(filters);
    res.json(inferences);
  } catch (error) {
    console.error('Error fetching inferences:', error);
    res.status(500).json({ error: 'Failed to fetch inferences' });
  }
});

// 特定の推論を取得
app.get('/api/inferences/:id', (req, res) => {
  try {
    const inference = inferencesRepository.getInference(req.params.id);
    if (!inference) {
      return res.status(404).json({ error: 'Inference not found' });
    }
    res.json(inference);
  } catch (error) {
    console.error(`Error fetching inference ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to fetch inference' });
  }
});

// 推論を作成
app.post('/api/inferences', (req, res) => {
  try {
    const inference = inferencesRepository.createInference(req.body);
    res.status(201).json(inference);
  } catch (error) {
    console.error('Error creating inference:', error);
    res.status(500).json({ error: 'Failed to create inference' });
  }
});

// 推論を更新
app.put('/api/inferences/:id', (req, res) => {
  try {
    const inference = inferencesRepository.updateInference(req.params.id, req.body);
    if (!inference) {
      return res.status(404).json({ error: 'Inference not found' });
    }
    res.json(inference);
  } catch (error) {
    console.error(`Error updating inference ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to update inference' });
  }
});

// 推論を削除
app.delete('/api/inferences/:id', (req, res) => {
  try {
    const success = inferencesRepository.deleteInference(req.params.id);
    if (!success) {
      return res.status(404).json({ error: 'Inference not found' });
    }
    res.status(204).send();
  } catch (error) {
    console.error(`Error deleting inference ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to delete inference' });
  }
});

// 推論を実行
app.post('/api/inferences/:id/run', async (req, res) => {
  try {
    const success = await inferencesRepository.runInference(req.params.id);
    if (!success) {
      return res.status(400).json({ error: 'Failed to run inference' });
    }
    const inference = inferencesRepository.getInference(req.params.id);
    res.json(inference);
  } catch (error) {
    console.error(`Error running inference ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to run inference' });
  }
});

// 推論結果を取得
app.get('/api/inferences/:id/results', (req, res) => {
  try {
    const results = inferencesRepository.getInferenceResults(req.params.id);
    res.json(results);
  } catch (error) {
    console.error(`Error fetching results for inference ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to fetch inference results' });
  }
});

// 推論にメトリクスを適用
app.post('/api/inferences/:id/apply-metrics', (req, res) => {
  try {
    const metrics = metricsRepository.calculateAndApplyMetrics(req.params.id);
    if (!metrics) {
      return res.status(400).json({ error: 'Failed to calculate metrics' });
    }
    res.json({ metrics });
  } catch (error) {
    console.error(`Error applying metrics to inference ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to apply metrics' });
  }
});

// --------------------------------------------------
// 評価指標関連エンドポイント
// --------------------------------------------------

// 評価指標一覧を取得
app.get('/api/metrics', (req, res) => {
  try {
    const metrics = metricsRepository.getMetrics();
    res.json(metrics);
  } catch (error) {
    console.error('Error fetching metrics:', error);
    res.status(500).json({ error: 'Failed to fetch metrics' });
  }
});

// 特定の評価指標を取得
app.get('/api/metrics/:id', (req, res) => {
  try {
    const metric = metricsRepository.getMetric(req.params.id);
    if (!metric) {
      return res.status(404).json({ error: 'Metric not found' });
    }
    res.json(metric);
  } catch (error) {
    console.error(`Error fetching metric ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to fetch metric' });
  }
});

// 評価指標を作成
app.post('/api/metrics', (req, res) => {
  try {
    const metric = metricsRepository.createMetric(req.body);
    res.status(201).json(metric);
  } catch (error) {
    console.error('Error creating metric:', error);
    res.status(500).json({ error: 'Failed to create metric' });
  }
});

// 評価指標を更新
app.put('/api/metrics/:id', (req, res) => {
  try {
    const metric = metricsRepository.updateMetric(req.params.id, req.body);
    if (!metric) {
      return res.status(404).json({ error: 'Metric not found' });
    }
    res.json(metric);
  } catch (error) {
    console.error(`Error updating metric ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to update metric' });
  }
});

// 評価指標を削除
app.delete('/api/metrics/:id', (req, res) => {
  try {
    const success = metricsRepository.deleteMetric(req.params.id);
    if (!success) {
      return res.status(404).json({ error: 'Metric not found' });
    }
    res.status(204).send();
  } catch (error) {
    console.error(`Error deleting metric ${req.params.id}:`, error);
    res.status(500).json({ error: 'Failed to delete metric' });
  }
});

// リーダーボードを取得
app.get('/api/leaderboard', (req, res) => {
  try {
    const filters = {
      datasetId: req.query.datasetId as string,
      providerId: req.query.providerId as string,
      modelId: req.query.modelId as string,
      metricId: req.query.metricId as string,
      limit: req.query.limit ? parseInt(req.query.limit as string) : undefined
    };
    
    const leaderboard = metricsRepository.getLeaderboard(filters);
    res.json(leaderboard);
  } catch (error) {
    console.error('Error fetching leaderboard:', error);
    res.status(500).json({ error: 'Failed to fetch leaderboard' });
  }
});

export default app;
