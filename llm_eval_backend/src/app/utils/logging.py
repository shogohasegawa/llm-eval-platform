import mlflow
from mlflow.entities import ViewType
from typing import Dict
import logging
import asyncio
import datetime
import time
import hashlib

from app.config.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def log_evaluation_results(model_name: str, metrics: Dict[str, float]) -> bool:
    """
    MLflowにモデル評価結果をログします。
    非同期関数として実装し、バックグラウンドタスクとして実行できるようにします。
    同じモデル名の場合は既存のRunを更新します。

    Args:
        model_name: モデル名（形式: provider/model）
        metrics: 評価メトリクスの辞書

    Returns:
        True: ロギングが成功した場合
        False: ロギングが失敗した場合
    """
    # Log a sample of metrics for debugging
    metrics_sample = list(metrics.items())[:5] if metrics else []
    logger.info(f"🪵 log_evaluation_results called for {model_name} with {len(metrics)} metrics: {metrics_sample}")
    
    try:
        logger.info(f"🪵 Logging to MLflow: {model_name} with metrics {list(metrics.keys())}")

        # Skip if metrics are empty
        if not metrics:
            logger.warning(f"MLflow logging skipped for {model_name} - No metrics to log")
            return False

        # Run MLflow operations synchronously in a separate thread
        def _do_mlflow_logging():
            try:
                # Set MLflow tracking URI
                if settings.MLFLOW_TRACKING_URI:
                    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
                    logger.info(f"MLflow tracking URI set to: {settings.MLFLOW_TRACKING_URI}")
                else:
                    logger.warning("MLflow tracking URI not set in settings, using default")
                
                # Log MLflow version and tracking URI for debugging
                logger.info(f"MLflow version: {mlflow.__version__}")
                logger.info(f"Current MLflow tracking URI: {mlflow.get_tracking_uri()}")
                
                # Create or get experiment
                experiment_name = "model_evaluation"
                mlflow.set_experiment(experiment_name)
                
                # Get experiment info
                experiment = mlflow.get_experiment_by_name(experiment_name)
                logger.info(f"Using experiment: {experiment_name} (ID: {experiment.experiment_id})")
                
                # 既存のランを検索する
                run_id = None
                try:
                    # MLflow クライアントを使用
                    from mlflow.client import MlflowClient
                    client = MlflowClient()
                    
                    # 常に"base"タグが付いた親ランを検索（n_shotsに関係なく同じランを使用）
                    # モデル名だけを条件にすることで、異なるn_shotsでも同じランを使う
                    run_filter = f"params.model_name = '{model_name}' and tags.run_type = 'base'"
                    logger.info(f"Searching for existing base run with filter: {run_filter}")
                    matching_runs = client.search_runs(
                        experiment_ids=[experiment.experiment_id],
                        filter_string=run_filter,
                        max_results=1
                    )
                    
                    # 同じモデル名でランが存在する場合は、そのランを再利用
                    run_id = None
                    if matching_runs:
                        run_id = matching_runs[0].info.run_id
                        logger.info(f"Found existing run for {model_name} with ID: {run_id}, will update it")
                    
                except Exception as search_error:
                    logger.error(f"Error searching for runs: {str(search_error)}")
                    run_id = None
                
                try:
                    # 既存のランが見つかった場合は、そのランをロードして更新
                    if run_id:
                        logger.info(f"Loading existing run with ID: {run_id}")
                        run = mlflow.start_run(run_id=run_id)
                    else:
                        # 既存のランがない場合は新しいランを作成
                        logger.info(f"No existing run found for {model_name}, creating new run")
                        run = mlflow.start_run(run_name=model_name)
                        
                        # 新規ランの場合のみパラメータをログ
                        mlflow.log_param("model_name", model_name)
                        mlflow.log_param("created_at", datetime.datetime.now().isoformat())
                        mlflow.log_param("model_type", model_name.split(':')[0] if ':' in model_name else model_name)
                        mlflow.log_param("supported_n_shots", "0,1,2,3,4,5")
                        
                        # 新規ランに必ずbaseタグを付ける
                        client.set_tag(run.info.run_id, "run_type", "base")
                        logger.info(f"✅ Tagged new run as 'base'")
                    
                    run_id = run.info.run_id
                    logger.info(f"Run loaded/created with ID: {run_id}")
                    
                    # 更新時刻をタグとしてログ（タグは何度でも更新可能）
                    try:
                        client.set_tag(run_id, "last_updated_at", datetime.datetime.now().isoformat())
                        logger.info(f"✅ Updated 'last_updated_at' tag for run {run_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not update 'last_updated_at' tag: {str(e)}")
                    
                    # n_shots 値を取得（これは後でメトリクスのステップ値として使用）
                    n_shots_value = 0
                    if "n_shots_value" in metrics:
                        n_shots_value = metrics.pop("n_shots_value")
                        logger.info(f"Using n_shots value from metrics: {n_shots_value}")
                    else:
                        logger.warning("n_shots_value not found in metrics, defaulting to 0")
                    
                    # n_shots 値をランのタグとして記録（表示では使わないが、デバッグに便利）
                    client.set_tag(run_id, f"n_shots_{n_shots_value}_updated_at", datetime.datetime.now().isoformat())
                    
                    # Filter and convert metrics to numeric values
                    numeric_metrics = {}
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            try:
                                numeric_metrics[key] = float(value)
                            except (ValueError, TypeError):
                                logger.warning(f"⚠️ Could not convert metric {key} to float: {value}")
                        else:
                            # Try to convert string numbers to float
                            if isinstance(value, str):
                                try:
                                    numeric_value = float(value)
                                    numeric_metrics[key] = numeric_value
                                    logger.info(f"🔄 Converted string metric {key} to float: {numeric_value}")
                                    continue
                                except (ValueError, TypeError):
                                    pass
                            logger.warning(f"⚠️ Skipping non-numeric metric {key}: {value} (type: {type(value).__name__})")
                    
                    # Log all metrics at once using log_metrics (more reliable than individual log_metric calls)
                    if numeric_metrics:
                        try:
                            formatted_metrics = dict(sorted(numeric_metrics.items()))
                            logger.info(f"📊 Logging all metrics at once to MLflow: {list(formatted_metrics.keys())}")
                            
                            # メトリクスをより詳細に表示（デバッグ用）
                            for metric_name, metric_value in formatted_metrics.items():
                                logger.info(f"📊 MLflow記録予定メトリクス: {metric_name} = {metric_value} (type: {type(metric_value).__name__})")
                            
                            # Get existing metrics to check for conflicts
                            existing_metrics = {}
                            try:
                                from mlflow.tracking.client import MlflowClient
                                client = MlflowClient()
                                run_data = client.get_run(run_id).data
                                for key, value in run_data.metrics.items():
                                    existing_metrics[key] = value
                                logger.info(f"Found {len(existing_metrics)} existing metrics in run {run_id}")
                            except Exception as e:
                                logger.warning(f"Could not retrieve existing metrics: {str(e)}")
                            
                            # すべてのメトリクスを n_shots_value をステップとして使用し、統一的にログ記録
                            logger.info(f"Logging {len(formatted_metrics)} metrics with n_shots={n_shots_value} as step")
                            logged_count = 0
                            
                            # n_shots_value はメトリクスではなく、ステップとして使用するので除外
                            if "n_shots_value" in formatted_metrics:
                                formatted_metrics.pop("n_shots_value")
                            
                            # メトリクス名を完全に正規化する新しいアプローチ
                            cleaned_metrics = {}
                            for key, value in formatted_metrics.items():
                                logger.info(f"📊 メトリクス名正規化処理: '{key}'")
                                
                                # いったん "_" で分割
                                parts = key.split("_")
                                # 最初からやり直して正規化された形式に構築
                                
                                # 1. n_shotパターンを特定
                                shot_pattern = None
                                for part in parts:
                                    if part.endswith('shot'):
                                        shot_pattern = part
                                        break
                                
                                if shot_pattern:
                                    shot_num = shot_pattern.replace('shot', '')
                                    
                                    # 2. メトリクス名部分を特定（最後の部分）
                                    metric_name = parts[-1]
                                    
                                    # 3. データセット名を特定（最初のshotパターン前までの部分）
                                    dataset_parts = []
                                    for part in parts:
                                        if part.endswith('shot'):
                                            break
                                        dataset_parts.append(part)
                                    
                                    # データセット名がない場合はダミー名を使用
                                    dataset_name = "_".join(dataset_parts) if dataset_parts else "dataset"
                                    
                                    # 4. 正規化された形式に再構築
                                    normalized_key = f"{dataset_name}_{shot_num}shot_{metric_name}"
                                    logger.info(f"📊 メトリクス名正規化: '{key}' → '{normalized_key}'")
                                    
                                    cleaned_metrics[normalized_key] = value
                                else:
                                    # shot情報が含まれていない場合はそのまま
                                    logger.info(f"📊 shot情報なし、そのまま使用: '{key}'")
                                    cleaned_metrics[key] = value
                            
                            # 元のメトリクスを置き換え
                            formatted_metrics = cleaned_metrics
                            
                            # すべてのメトリクスを同じn_shots値をステップとして記録
                            for key, value in formatted_metrics.items():
                                try:
                                    mlflow.log_metric(key, value, step=n_shots_value)
                                    logger.info(f"✅ Logged metric {key} = {value} with step={n_shots_value}")
                                    logged_count += 1
                                except Exception as e:
                                    logger.error(f"❌ Failed to log metric {key}: {str(e)}")
                            
                            logger.info(f"✅ Successfully logged {logged_count}/{len(formatted_metrics)} metrics to MLflow")
                        except Exception as metrics_error:
                            logger.error(f"❌ Error logging metrics to MLflow: {str(metrics_error)}", exc_info=True)
                            # Fall back to logging metrics one by one
                            logger.info("🔄 Trying to log metrics one by one as fallback")
                            
                            # n_shots_value はメトリクスではなく、ステップとして使用するので除外
                            if "n_shots_value" in numeric_metrics:
                                numeric_metrics.pop("n_shots_value")
                            
                            logged_metrics_count = 0
                            for key, value in numeric_metrics.items():
                                try:
                                    # すべてのメトリクスを同じステップで記録
                                    logger.info(f"📊 個別にログ: {key} = {value} with step={n_shots_value}")
                                    mlflow.log_metric(key, value, step=n_shots_value)
                                    logged_metrics_count += 1
                                except Exception as e:
                                    logger.error(f"❌ Failed to log metric {key}: {str(e)}")
                            logger.info(f"✅ Logged {logged_metrics_count}/{len(numeric_metrics)} metrics individually")
                    
                    logger.info(f"All MLflow logging operations completed")
                    
                    # Display MLflow UI URLs for easier debugging
                    tracking_uri = mlflow.get_tracking_uri()
                    if tracking_uri.startswith("http"):
                        logger.info(f"MLflow Run URL: {tracking_uri}/#/experiments/{experiment.experiment_id}/runs/{run_id}")
                        logger.info(f"MLflow Experiment URL: {tracking_uri}/#/experiments/{experiment.experiment_id}")
                    
                    # ランを終了
                    mlflow.end_run()
                    logger.info(f"MLflow logging completed for {model_name} with n_shots={n_shots_value}")
                    return True
                except Exception as run_error:
                    logger.error(f"Error during MLflow run: {str(run_error)}")
                    # Make sure to end the run
                    try:
                        mlflow.end_run()
                    except:
                        pass
                    return False
            except Exception as e:
                logger.error(f"Error in MLflow logging: {str(e)}")
                return False

        # Run the MLflow logging function in a separate thread
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _do_mlflow_logging)
        return result
    except Exception as e:
        logger.error(f"Exception in log_evaluation_results: {str(e)}")
        return False