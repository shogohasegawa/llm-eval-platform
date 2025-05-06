"""
評価ジョブマネージャモジュール

バックグラウンドでの評価ジョブ処理を管理します。
"""
import asyncio
import json
import logging
import time
import traceback
from typing import Dict, Any, Optional, List
import datetime

from app.api.models import EvaluationRequest, JobStatus, JobLogLevel
from app.utils.db.jobs import get_job_repository
from app.core.evaluation import run_multiple_evaluations
from app.utils.logging import log_evaluation_results
from app.utils.litellm_helper import get_provider_options

# ロガーの設定
logger = logging.getLogger(__name__)


class JobManager:
    """
    評価ジョブを管理するクラス
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """シングルトンパターンでインスタンスを提供"""
        if cls._instance is None:
            cls._instance = super(JobManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """ジョブマネージャの初期化"""
        if self._initialized:
            return
        
        self.job_repo = get_job_repository()
        self._initialized = True
    
    async def submit_job(self, request: EvaluationRequest) -> Dict[str, Any]:
        """
        評価ジョブをサブミット
        
        Args:
            request: 評価リクエスト
                
        Returns:
            作成されたジョブ情報
        """
        # ジョブをデータベースに作成
        job = self.job_repo.create_job(request)
        
        # ログを追加
        self.job_repo.add_job_log(
            job_id=job["id"],
            log_level=JobLogLevel.INFO,
            message="ジョブがキューに追加されました"
        )
        
        # 非同期でジョブを実行
        asyncio.create_task(self._run_job(job["id"], request))
        
        return job
    
    async def _run_job(self, job_id: str, request: EvaluationRequest):
        """
        非同期でジョブを実行
        
        Args:
            job_id: ジョブID
            request: 評価リクエスト
        """
        try:
            # ジョブステータスを「実行中」に更新
            self.job_repo.update_job_status(job_id, JobStatus.RUNNING)
            
            # ログを追加
            self.job_repo.add_job_log(
                job_id=job_id,
                log_level=JobLogLevel.INFO,
                message="ジョブの実行を開始しました"
            )
            
            # リクエストからモデル情報と追加パラメータを取得
            provider_name = request.model.provider
            model_name = request.model.model_name
            
            # 追加パラメータを準備（プロバイダごとのデフォルト設定を適用）
            additional_params = get_provider_options(provider_name)
            
            # ユーザー指定の追加パラメータを適用（優先）
            if request.model.additional_params:
                # ヘッダーの場合は更新
                if "headers" in additional_params and "headers" in request.model.additional_params:
                    additional_params["headers"].update(request.model.additional_params["headers"])
                    # ヘッダーをリクエストの追加パラメータから削除（重複適用を避けるため）
                    user_params = request.model.additional_params.copy()
                    user_params.pop("headers", None)
                    additional_params.update(user_params)
                else:
                    # ヘッダーがない場合はそのまま更新
                    additional_params.update(request.model.additional_params)
            
            # データセット処理開始ログ
            datasets_str = ", ".join(request.datasets)
            self.job_repo.add_job_log(
                job_id=job_id,
                log_level=JobLogLevel.INFO,
                message=f"データセット {datasets_str} の評価を開始しました"
            )
            
            # 評価エンジン呼び出し
            results_full: Dict[str, Any] = await run_multiple_evaluations(
                datasets=request.datasets,
                provider_name=provider_name,
                model_name=model_name,
                num_samples=request.num_samples,
                n_shots=request.n_shots,
                additional_params=additional_params
            )
            
            # フラットなメトリクス辞書を作成
            flat_metrics: Dict[str, float] = {}
            for ds, ds_res in results_full.get("results", {}).items():
                details = ds_res.get("details", {})
                for key, value in details.items():
                    if key.endswith("_details") or key.endswith("_error_rate"):
                        continue
                    flat_metrics[key] = value  # 例: "aio_0shot_char_f1": 0.11
                
                # データセット完了ログ
                self.job_repo.add_job_log(
                    job_id=job_id,
                    log_level=JobLogLevel.INFO,
                    message=f"データセット {ds} の評価が完了しました"
                )
            
            # MLflowへログ
            if flat_metrics and len(flat_metrics) > 0:
                try:
                    # デバッグ用ログ - メトリクスデータの例を出力
                    metrics_sample = list(flat_metrics.items())[:5]
                    logger.info(f"📊 ジョブマネージャー: MLflowへのメトリクスログを開始します - モデル: {provider_name}/{model_name}")
                    logger.info(f"📊 メトリクスデータの例 (5件): {metrics_sample}")
                    
                    # メトリクスデータのログファイルを作成（トラブルシューティング用）
                    metrics_log_file = f"/app/job_metrics_{provider_name}_{model_name}_{int(time.time())}.json"
                    with open(metrics_log_file, "w") as f:
                        json.dump({
                            "provider": provider_name,
                            "model": model_name,
                            "timestamp": datetime.datetime.now().isoformat(),
                            "metrics": flat_metrics
                        }, f, indent=2)
                    logger.info(f"📊 ジョブメトリクスデータをログファイルに保存しました: {metrics_log_file}")
                    
                    # MLflowへのロギング実行
                    logging_result = await log_evaluation_results(
                        model_name=f"{provider_name}/{model_name}",
                        metrics=flat_metrics
                    )
                    
                    # ログ結果をジョブログに記録
                    if logging_result:
                        self.job_repo.add_job_log(
                            job_id=job_id,
                            log_level=JobLogLevel.INFO,
                            message=f"MLflowへのメトリクスのロギングが完了しました（{len(flat_metrics)}個のメトリクス）"
                        )
                        logger.info(f"✅ MLflowロギング成功: {provider_name}/{model_name}")
                    else:
                        self.job_repo.add_job_log(
                            job_id=job_id,
                            log_level=JobLogLevel.WARNING,
                            message="MLflowへのロギングに問題が発生しました"
                        )
                        logger.warning(f"⚠️ MLflowロギング問題: {provider_name}/{model_name}")
                except Exception as e:
                    # MLflowロギングエラーはジョブ全体を失敗にはしない
                    error_msg = str(e)
                    logger.error(f"❌ MLflowロギングエラー: {error_msg}")
                    
                    # エラーをファイルに記録
                    error_log_file = f"/app/job_mlflow_error_{provider_name}_{model_name}_{int(time.time())}.txt"
                    with open(error_log_file, "w") as f:
                        f.write(f"Error logging metrics for {provider_name}/{model_name}: {error_msg}\n\n")
                        import traceback
                        traceback.print_exc(file=f)
                    logger.error(f"❌ ジョブエラーログをファイルに保存しました: {error_log_file}")
                    
                    self.job_repo.add_job_log(
                        job_id=job_id,
                        log_level=JobLogLevel.ERROR,
                        message=f"MLflowへのロギング中にエラーが発生: {error_msg}"
                    )
            else:
                # メトリクスがない場合はログを記録するだけ
                logger.warning(f"MLflowへのロギングをスキップ: メトリクスがありません - モデル: {provider_name}/{model_name}")
                self.job_repo.add_job_log(
                    job_id=job_id,
                    log_level=JobLogLevel.WARNING,
                    message="メトリクスが空のためMLflowへのロギングをスキップしました"
                )
            
            # ジョブ完了ログ
            self.job_repo.add_job_log(
                job_id=job_id,
                log_level=JobLogLevel.INFO,
                message="ジョブが正常に完了しました"
            )
            
            # 結果を保存してジョブステータスを「完了」に更新
            response_data = {
                "model_info": request.model.dict(),
                "metrics": flat_metrics,
                "full_results": results_full
            }
            self.job_repo.update_job_status(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                result_data=response_data
            )
            
        except Exception as e:
            # エラーをログに記録
            error_msg = str(e)
            logger.error(f"ジョブ実行エラー (Job ID: {job_id}): {error_msg}")
            
            # ジョブログにエラーを追加
            self.job_repo.add_job_log(
                job_id=job_id,
                log_level=JobLogLevel.ERROR,
                message=f"ジョブ実行中にエラーが発生しました: {error_msg}"
            )
            
            # ジョブステータスを「失敗」に更新
            self.job_repo.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error_message=error_msg
            )
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        ジョブ情報を取得
        
        Args:
            job_id: ジョブID
                
        Returns:
            ジョブ情報またはNone
        """
        return self.job_repo.get_job_by_id(job_id)
    
    def get_all_jobs(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        すべてのジョブを取得
        
        Args:
            page: ページ番号
            page_size: 1ページあたりの件数
                
        Returns:
            ジョブリスト情報
        """
        jobs, total = self.job_repo.get_all_jobs(page, page_size)
        return {
            "jobs": jobs,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    
    def get_job_logs(self, job_id: str) -> List[Dict[str, Any]]:
        """
        ジョブのログを取得
        
        Args:
            job_id: ジョブID
                
        Returns:
            ログエントリのリスト
        """
        return self.job_repo.get_job_logs(job_id)


# シングルトンインスタンスを取得する関数
def get_job_manager() -> JobManager:
    """
    ジョブマネージャのシングルトンインスタンスを取得
    
    Returns:
        JobManagerインスタンス
    """
    return JobManager()
