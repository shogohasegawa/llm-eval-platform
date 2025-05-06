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
                    
                    # フィルターを使用して同じモデル名のランを検索
                    run_filter = f"params.model_name = '{model_name}'"
                    logger.info(f"Searching for existing runs with filter: {run_filter}")
                    matching_runs = client.search_runs(
                        experiment_ids=[experiment.experiment_id],
                        filter_string=run_filter
                    )
                    
                    # 同じモデル名でランが存在する場合は、そのランを再利用
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
                    
                    run_id = run.info.run_id
                    logger.info(f"Run loaded/created with ID: {run_id}")
                    
                    # 更新時刻をログ
                    mlflow.log_param("updated_at", datetime.datetime.now().isoformat())
                    
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
                            logger.info(f"📊 Logging all metrics at once to MLflow: {list(numeric_metrics.keys())}")
                            mlflow.log_metrics(numeric_metrics)
                            logger.info(f"✅ Successfully logged {len(numeric_metrics)} metrics to MLflow")
                        except Exception as metrics_error:
                            logger.error(f"❌ Error logging metrics to MLflow: {str(metrics_error)}", exc_info=True)
                            # Fall back to logging metrics one by one
                            logger.info("🔄 Trying to log metrics one by one as fallback")
                            logged_metrics_count = 0
                            for key, value in numeric_metrics.items():
                                try:
                                    mlflow.log_metric(key, value)
                                    logged_metrics_count += 1
                                except Exception as e:
                                    logger.error(f"❌ Failed to log metric {key}: {str(e)}")
                            logger.info(f"✅ Logged {logged_metrics_count}/{len(numeric_metrics)} metrics individually")
                    
                    logger.info(f"All MLflow logging operations completed")
                    
                    # Display MLflow UI URL for easier debugging
                    tracking_uri = mlflow.get_tracking_uri()
                    if tracking_uri.startswith("http"):
                        logger.info(f"MLflow UI URL: {tracking_uri}/#/experiments/{experiment.experiment_id}/runs/{run_id}")
                    
                    # End the run
                    mlflow.end_run()
                    logger.info(f"MLflow logging completed for {model_name}")
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