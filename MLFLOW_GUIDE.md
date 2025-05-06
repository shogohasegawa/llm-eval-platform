# MLflow統合ガイド

## 概要

LLM評価プラットフォームはMLflowを使用して評価メトリクスを追跡・可視化します。各モデル評価は一意のMLflow Runとして記録され、異なるデータセットに対するモデルパフォーマンスを比較できます。

## 主な機能

- **モデルごとの1行表示**: 同じモデル名のランは1つのMLflow Runにまとめられます
- **メトリクスの上書きと追記**:
  - 同じデータセット・評価指標: 新しい値で上書き
  - 異なるデータセット・評価指標: 既存のメトリクスに追加
- **自動型変換**: 文字列メトリクスは可能な限り数値に変換されます
- **エラーハンドリング**: 包括的なエラー処理とフォールバックメカニズム

## MLflowアーキテクチャ

- **MLflowサーバー**: Dockerコンテナとして実行 (`mlflow`サービス in docker-compose.yml)
- **トラッキングURI**: http://mlflow:5000 (Docker内部ネットワーク)
- **実験**: すべてのモデル評価は "model_evaluation" 実験に保存
- **ラン**: 各モデル評価は別々のランとして作成され、モデル名がラン名として使用
- **メトリクス**: 評価から得られた数値メトリクスがMLflowに記録

## MLflowログ機能の実装について

主要な実装は次のファイルにあります:
- `logging.py`: MLflowログ機能を提供
- `job_manager.py`: 評価後にロギングを呼び出し
- `inferences.py`: 評価結果を処理

### 重要な改良点

1. **既存ランの再利用**:
   ```python
   # 同じモデル名のランを検索
   run_filter = f"params.model_name = '{model_name}'"
   matching_runs = client.search_runs(
       experiment_ids=[experiment.experiment_id],
       filter_string=run_filter
   )
   
   # 既存のランがあればそれを使用
   if matching_runs:
       run_id = matching_runs[0].info.run_id
       run = mlflow.start_run(run_id=run_id)
   ```

2. **文字列メトリクスの数値変換**:
   ```python
   if isinstance(value, str):
       try:
           numeric_value = float(value)
           numeric_metrics[key] = numeric_value
           continue
       except (ValueError, TypeError):
           pass
   ```

3. **バッチメトリクスログ**:
   ```python
   # すべてのメトリクスを一度にログ
   mlflow.log_metrics(numeric_metrics)
   ```

## MLflow UIへのアクセス

MLflow UIには以下の方法でアクセスできます:

1. **APIプロキシ経由** (推奨): http://localhost:8001/proxy-mlflow/
2. **MLflowデバッグページ**: http://localhost:8001/debug-mlflow

## トラブルシューティング

メトリクスがMLflowに表示されない場合:

1. **接続確認**: MLflowコンテナが実行中でAPIコンテナからアクセス可能か確認:
   ```
   docker-compose ps
   ```

2. **ログ確認**: MLflow関連のログメッセージを確認:
   ```
   docker-compose logs -f api | grep MLflow
   ```

3. **パラメータの確認**: MLflowのRunを開き、パラメータに`model_name`が正しく設定されているか確認

4. **実験の確認**: MLflowの実験一覧で`model_evaluation`が存在することを確認

## 注意事項

1. **メトリクス名**: メトリクス名は一貫して使用してください (例: `aio_0shot_accuracy`)
2. **モデル名**: モデル名は一貫したフォーマットで使用してください (例: `provider/model`)
3. **非数値データ**: 非数値データはMLflowにログされません (例: JSONやテキスト)