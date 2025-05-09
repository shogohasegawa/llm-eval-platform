from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from typing import Dict, Any, List, Optional, Union
import datetime
import time
import json
import traceback
import logging

from app.api.models import (
    EvaluationRequest, EvaluationResponse, MetricInfo, MetricsListResponse,
    AsyncEvaluationResponse, JobStatus, JobDetail, JobSummary, JobListResponse, JobLog, JobLogLevel
)
from app.core.evaluation import run_multiple_evaluations
from app.utils.logging import log_evaluation_results
from app.utils.litellm_helper import get_provider_options
from app.metrics import METRIC_REGISTRY
from app.utils.job_manager import get_job_manager

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/metrics", response_model=MetricsListResponse)
async def get_available_metrics() -> MetricsListResponse:
    """
    利用可能な評価指標一覧を返す

    Returns:
        MetricsListResponse: 評価指標名、説明、パラメータ定義のリスト
    """
    metrics_list: List[MetricInfo] = []
    
    # METRIC_REGISTRYから登録されている評価指標を取得
    for name, metric_cls in METRIC_REGISTRY.items():
        # インスタンスを作成して情報を取得
        metric_instance = metric_cls()
        
        # docstringから説明を取得（可能であれば）
        description = None
        if metric_cls.__doc__:
            description = metric_cls.__doc__.strip()
        
        # パラメータ定義を取得
        param_defs = metric_cls.get_parameter_definitions()
        parameters = {}
        
        # パラメータ定義をAPIモデルに変換
        for param_name, param_def in param_defs.items():
            parameters[param_name] = MetricParameterInfo(
                type=param_def.get("type", "string"),
                description=param_def.get("description"),
                default=param_def.get("default"),
                required=param_def.get("required", False),
                enum=param_def.get("enum")
            )
        
        metrics_list.append(
            MetricInfo(
                name=name,
                description=description,
                parameters=parameters if parameters else None,
                is_higher_better=getattr(metric_instance, "is_higher_better", True)
            )
        )
    
    # 名前でソート
    metrics_list.sort(key=lambda x: x.name)
    
    return MetricsListResponse(metrics=metrics_list)


@router.post("/run", response_model=Union[EvaluationResponse, AsyncEvaluationResponse])
async def evaluate(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks
) -> Union[EvaluationResponse, AsyncEvaluationResponse]:
    """
    複数データセットに対するLLM評価を実行し、
    使用したモデル情報とフラットメトリクスのみを返却するシンプルエンドポイント。
    
    async_execution=Trueの場合は、非同期実行となり、AsyncEvaluationResponseが返却される。

    Args:
        request (EvaluationRequest): 評価対象データセット、モデル設定、サンプル数、few-shot数
        background_tasks (BackgroundTasks): バックグラウンドタスク登録用

    Returns:
        Union[EvaluationResponse, AsyncEvaluationResponse]: 
            同期実行の場合は使用モデル情報とメトリクスの辞書、
            非同期実行の場合はジョブIDとステータス
    """
    # 非同期実行の場合
    if request.async_execution:
        try:
            job_manager = get_job_manager()
            job = await job_manager.submit_job(request)
            
            return AsyncEvaluationResponse(
                job_id=job["id"],
                status=JobStatus(job["status"]),
                message="ジョブが正常にキューに追加されました"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"非同期ジョブの登録に失敗しました: {str(e)}")
    
    # 同期実行の場合（既存の処理）
    try:
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
        
        # 1) 評価エンジン呼び出し
        results_full: Dict[str, Any] = await run_multiple_evaluations(
            datasets=request.datasets,
            provider_name=provider_name,
            model_name=model_name,
            num_samples=request.num_samples,
            n_shots=request.n_shots,
            additional_params=additional_params
        )

        # 2) フラットなメトリクス辞書を作成 - シンプルな解決策
        flat_metrics: Dict[str, float] = {}
        for ds, ds_res in results_full.get("results", {}).items():
            details = ds_res.get("details", {})
            # クリーン化されたデータセット名を取得
            clean_dataset_name = ds_res.get("metadata", {}).get("dataset", ds)
            logger.info(f"📊 フラットメトリクス作成: dataset={ds}, clean_name={clean_dataset_name}")
            
            for key, value in details.items():
                # 詳細結果と誤差率は除外
                if key.endswith("_details") or key.endswith("_error_rate") or key.endswith("_parameters"):
                    continue
                
                # メトリクスをそのまま使用（前段階で正規化済み）
                flat_metrics[key] = value

        # 3) バックグラウンドでMLflowへログ（デバッグ有効化）
        try:
            logger.info(f"📊 リクエスト処理完了: MLflowにロギングを開始します: {provider_name}/{model_name}")
            logger.info(f"📊 メトリクスデータの例 (最大10件): {list(flat_metrics.items())[:10]}")
            
            # メトリクスデータのログファイルを作成（トラブルシューティング用）
            metrics_log_file = f"/app/debug_metrics_{provider_name}_{model_name}_{int(time.time())}.json"
            with open(metrics_log_file, "w") as f:
                json.dump({
                    "provider": provider_name,
                    "model": model_name,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "metrics": flat_metrics
                }, f, indent=2)
            logger.info(f"📊 メトリクスデータをログファイルに保存しました: {metrics_log_file}")
            
            # バックグラウンドタスクではなく直接実行してデバッグ（本番では戻す）
            logging_result = await log_evaluation_results(
                model_name=f"{provider_name}/{model_name}",
                metrics=flat_metrics
            )
            logger.info(f"📊 MLflowロギング結果: {logging_result}")
            
            if not logging_result:
                logger.error(f"❌ MLflowへのロギングが失敗しました: {provider_name}/{model_name}")
        except Exception as e:
            logger.error(f"❌❌❌ MLflowロギング中に例外が発生: {str(e)}", exc_info=True)
            # エラーをファイルに記録
            error_log_file = f"/app/mlflow_error_{provider_name}_{model_name}_{int(time.time())}.txt"
            with open(error_log_file, "w") as f:
                f.write(f"Error logging metrics for {provider_name}/{model_name}: {str(e)}\n\n")
                import traceback
                traceback.print_exc(file=f)
            logger.error(f"❌ エラーログをファイルに保存しました: {error_log_file}")
        
        # 元のコード（現在は非活性）
        # background_tasks.add_task(
        #     log_evaluation_results,
        #     model_name=f"{provider_name}/{model_name}",
        #     metrics=flat_metrics
        # )

        # 4) シンプルレスポンス返却
        return EvaluationResponse(
            model_info=request.model,
            metrics=flat_metrics
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(10, ge=1, le=100, description="1ページあたりの件数")
) -> JobListResponse:
    """
    評価ジョブの一覧を取得
    
    Args:
        page: ページ番号（1以上）
        page_size: 1ページあたりの件数（1～100）
        
    Returns:
        JobListResponse: ジョブ一覧とページネーション情報
    """
    try:
        job_manager = get_job_manager()
        result = job_manager.get_all_jobs(page, page_size)
        
        # APIモデルに変換
        jobs = []
        for job in result["jobs"]:
            # リクエストデータから必要な情報を取得
            request_data = job["request_data"]
            if not request_data:
                continue
                
            model_info = request_data.get("model", {})
            
            # 必要なデータの変換
            created_at = datetime.fromisoformat(job["created_at"]) if job["created_at"] else None
            updated_at = datetime.fromisoformat(job["updated_at"]) if job["updated_at"] else None
            completed_at = datetime.fromisoformat(job["completed_at"]) if job["completed_at"] else None
            
            jobs.append(JobSummary(
                id=job["id"],
                status=JobStatus(job["status"]),
                datasets=request_data.get("datasets", []),
                model_info=model_info,
                created_at=created_at,
                updated_at=updated_at,
                completed_at=completed_at
            ))
        
        return JobListResponse(
            jobs=jobs,
            total=result["total"],
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ジョブ一覧の取得に失敗しました: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: str = Path(..., description="ジョブID")
) -> JobDetail:
    """
    特定の評価ジョブの詳細を取得
    
    Args:
        job_id: ジョブID
        
    Returns:
        JobDetail: ジョブの詳細情報
    """
    try:
        job_manager = get_job_manager()
        job = job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' が見つかりません")
        
        # APIモデルに変換
        created_at = datetime.fromisoformat(job["created_at"]) if job["created_at"] else None
        updated_at = datetime.fromisoformat(job["updated_at"]) if job["updated_at"] else None
        completed_at = datetime.fromisoformat(job["completed_at"]) if job["completed_at"] else None
        
        return JobDetail(
            id=job["id"],
            status=JobStatus(job["status"]),
            request=job["request_data"],
            result=job["result_data"],
            error_message=job["error_message"],
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ジョブ詳細の取得に失敗しました: {str(e)}")


@router.get("/jobs/{job_id}/logs", response_model=JobLog)
async def get_job_logs(
    job_id: str = Path(..., description="ジョブID")
) -> JobLog:
    """
    特定の評価ジョブのログを取得
    
    Args:
        job_id: ジョブID
        
    Returns:
        JobLog: ジョブのログエントリのリスト
    """
    try:
        job_manager = get_job_manager()
        
        # ジョブの存在確認
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' が見つかりません")
        
        # ログの取得
        logs = job_manager.get_job_logs(job_id)
        
        # APIモデルに変換
        log_entries = []
        for log in logs:
            timestamp = datetime.fromisoformat(log["timestamp"]) if log["timestamp"] else None
            log_entries.append({
                "id": log["id"],
                "job_id": log["job_id"],
                "log_level": JobLogLevel(log["log_level"]),
                "message": log["message"],
                "timestamp": timestamp
            })
        
        return JobLog(
            logs=log_entries,
            job_id=job_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ジョブログの取得に失敗しました: {str(e)}")
