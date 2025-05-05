"""
推論管理APIエンドポイント

推論のCRUD操作と実行を提供するエンドポイントを実装します。
"""
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Query, Path

from app.api.models import (
    Inference, 
    InferenceCreate, 
    InferenceUpdate, 
    InferenceStatus, 
    InferenceResult,
    InferenceListResponse,
    InferenceDetailResponse,
    ModelConfig,
    EvaluationRequest
)
from app.utils.db.models import get_model_repository
from app.utils.db.providers import get_provider_repository
from app.utils.db.inferences import get_inference_repository
from app.core.evaluation import run_multiple_evaluations
from app.utils.litellm_helper import get_provider_options

# ロガーの設定
logger = logging.getLogger("llmeval")

router = APIRouter(prefix="/inferences", tags=["inferences"])


@router.get("", response_model=List[Inference])
async def list_inferences(
    dataset_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    model_id: Optional[str] = None,
    status: Optional[str] = None
):
    """
    推論一覧を取得します。
    
    Args:
        dataset_id: データセットIDによるフィルタ
        provider_id: プロバイダIDによるフィルタ
        model_id: モデルIDによるフィルタ
        status: ステータスによるフィルタ
        
    Returns:
        List[Inference]: 推論一覧
    """
    try:
        # フィルター条件を作成
        filters = {}
        if dataset_id:
            filters["dataset_id"] = dataset_id
        if provider_id:
            filters["provider_id"] = provider_id
        if model_id:
            filters["model_id"] = model_id
        if status:
            filters["status"] = status
        
        # リポジトリから推論一覧を取得
        inference_repo = get_inference_repository()
        inferences = inference_repo.get_all_inferences(filters)
        
        # API応答モデルにマッピング
        result = []
        for inf in inferences:
            # 結果を変換
            results = []
            for res in inf.get("results", []):
                results.append(InferenceResult(
                    id=res["id"],
                    inference_id=res["inference_id"],
                    input=res["input"],
                    expected_output=res.get("expected_output"),
                    actual_output=res["actual_output"],
                    metrics=res.get("metrics"),
                    latency=res.get("latency"),
                    token_count=res.get("token_count"),
                    created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
                ))
            
            # 日付文字列をdatetimeに変換
            created_at = datetime.fromisoformat(inf["created_at"]) if isinstance(inf["created_at"], str) else inf["created_at"]
            updated_at = datetime.fromisoformat(inf["updated_at"]) if isinstance(inf["updated_at"], str) else inf["updated_at"]
            completed_at = None
            if inf.get("completed_at"):
                completed_at = datetime.fromisoformat(inf["completed_at"]) if isinstance(inf["completed_at"], str) else inf["completed_at"]
            
            # 推論オブジェクトを作成
            inference = Inference(
                id=inf["id"],
                name=inf["name"],
                description=inf.get("description"),
                dataset_id=inf["dataset_id"],
                provider_id=inf["provider_id"],
                model_id=inf["model_id"],
                status=InferenceStatus(inf["status"]),
                progress=inf["progress"],
                metrics=inf.get("metrics"),
                results=results,
                created_at=created_at,
                updated_at=updated_at,
                completed_at=completed_at,
                error=inf.get("error")
            )
            result.append(inference)
        
        return result
    except Exception as e:
        logger.error(f"推論一覧取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論一覧取得エラー: {str(e)}"
        )


@router.post("", response_model=Inference, status_code=status.HTTP_201_CREATED)
async def create_inference(
    inference_data: InferenceCreate,
    background_tasks: BackgroundTasks
):
    """
    新しい推論を作成し、バックエンドで評価を実行します。
    
    Args:
        inference_data: 作成する推論のデータ
        background_tasks: バックグラウンドタスク
        
    Returns:
        Inference: 作成された推論情報
    """
    try:
        # バリデーション
        if not inference_data.dataset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="データセットIDは必須です"
            )
            
        if not inference_data.provider_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="プロバイダIDは必須です"
            )
            
        if not inference_data.model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="モデルIDは必須です"
            )
            
        # データセット名を抽出（パスからファイル名を取得）
        # "test/example.json" -> "example"
        dataset_name = inference_data.dataset_id.split('/')[-1].replace('.json', '')
        
        # プロバイダとモデル情報の取得
        provider_repo = get_provider_repository()
        model_repo = get_model_repository()
        
        provider = provider_repo.get_provider_by_id(inference_data.provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダID '{inference_data.provider_id}' が見つかりません"
            )
        
        model = model_repo.get_model_by_id(inference_data.model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{inference_data.model_id}' が見つかりません"
            )
        
        provider_type = provider["type"]
        model_name = model["name"]
        
        # モデル設定を構築
        model_config = ModelConfig(
            provider=provider_type,  
            model_name=model_name,
            max_tokens=inference_data.max_tokens or 512,
            temperature=inference_data.temperature or 0.7,
            top_p=inference_data.top_p or 1.0
        )
        
        # 評価リクエストを構築
        evaluation_request = EvaluationRequest(
            datasets=[dataset_name],
            num_samples=inference_data.num_samples or 100,
            n_shots=[inference_data.n_shots or 0],
            model=model_config
        )
        
        logger.info(f"評価リクエスト: {evaluation_request}")
        
        # 新しい推論をデータベースに保存
        inference_repo = get_inference_repository()
        
        # パラメータを保存
        parameters = {
            "max_tokens": inference_data.max_tokens or 512,
            "temperature": inference_data.temperature or 0.7,
            "top_p": inference_data.top_p or 1.0,
            "num_samples": inference_data.num_samples or 100,
            "n_shots": inference_data.n_shots or 0
        }
        
        # 推論を作成（初期状態はPENDING）
        inference_db = inference_repo.create_inference({
            "name": inference_data.name,
            "description": inference_data.description,
            "dataset_id": inference_data.dataset_id,
            "provider_id": inference_data.provider_id,
            "model_id": inference_data.model_id,
            "status": InferenceStatus.PENDING,
            "progress": 0,
            "parameters": parameters
        })
        
        # 背景タスクで評価を実行
        background_tasks.add_task(
            execute_inference_evaluation,
            inference_id=inference_db["id"],
            evaluation_request=evaluation_request,
            provider_name=provider_type,
            model_name=model_name
        )
        
        # 結果を変換
        results = []
        for res in inference_db.get("results", []):
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            ))
        
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(inference_db["created_at"]) if isinstance(inference_db["created_at"], str) else inference_db["created_at"]
        updated_at = datetime.fromisoformat(inference_db["updated_at"]) if isinstance(inference_db["updated_at"], str) else inference_db["updated_at"]
        completed_at = None
        if inference_db.get("completed_at"):
            completed_at = datetime.fromisoformat(inference_db["completed_at"]) if isinstance(inference_db["completed_at"], str) else inference_db["completed_at"]
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=inference_db["id"],
            name=inference_db["name"],
            description=inference_db.get("description"),
            dataset_id=inference_db["dataset_id"],
            provider_id=inference_db["provider_id"],
            model_id=inference_db["model_id"],
            status=InferenceStatus(inference_db["status"]),
            progress=inference_db["progress"],
            metrics=inference_db.get("metrics"),
            results=results,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error=inference_db.get("error")
        )
        
        return inference
        
    except Exception as e:
        logger.error(f"推論作成エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論作成エラー: {str(e)}"
        )


# 背景タスクとして実行する評価関数
async def execute_inference_evaluation(
    inference_id: str,
    evaluation_request: EvaluationRequest,
    provider_name: str,
    model_name: str
):
    """
    推論評価を実行するバックグラウンドタスク
    
    Args:
        inference_id: 推論ID
        evaluation_request: 評価リクエスト
        provider_name: プロバイダー名
        model_name: モデル名
    """
    logger.info(f"推論 {inference_id} の評価を開始します")
    inference_repo = get_inference_repository()
    
    try:
        # 推論のステータスを更新
        inference_repo.update_inference(inference_id, {"status": InferenceStatus.RUNNING, "progress": 0})
        
        # 追加パラメータを準備（プロバイダごとのデフォルト設定を適用）
        additional_params = get_provider_options(provider_name)
        
        # 評価エンジン呼び出し
        results_full = await run_multiple_evaluations(
            datasets=evaluation_request.datasets,
            provider_name=provider_name,
            model_name=model_name,
            num_samples=evaluation_request.num_samples,
            n_shots=evaluation_request.n_shots,
            additional_params=additional_params
        )
        
        # フラットなメトリクス辞書を作成
        flat_metrics: Dict[str, float] = {}
        for ds, ds_res in results_full.get("results", {}).items():
            details = ds_res.get("details", {})
            for key, value in details.items():
                if key.endswith("_details") or key.endswith("_error_rate"):
                    continue
                flat_metrics[key] = value
                
                # エラー率も追加
                error_rate_key = f"{key}_error_rate"
                if error_rate_key in details:
                    flat_metrics[error_rate_key] = details[error_rate_key]
        
        # メトリクスが空の場合は警告
        if not flat_metrics:
            logger.warning(f"推論 {inference_id} のメトリクスが空です。評価が正しく行われなかった可能性があります。")
            # メトリクスが空でも完了とするが、エラーメッセージを設定
            inference_repo.update_inference(inference_id, {
                "status": InferenceStatus.COMPLETED,
                "progress": 100,
                "metrics": {},
                "error": "メトリクスの計算に失敗しました。データセットとモデルの組み合わせが適切か確認してください。"
            })
        else:
            # 推論のステータスを完了に更新（メトリクスあり）
            inference_repo.update_inference(inference_id, {
                "status": InferenceStatus.COMPLETED,
                "progress": 100,
                "metrics": flat_metrics,
                "error": None  # エラーフィールドをクリア
            })
        
        logger.info(f"推論 {inference_id} の評価が完了しました")
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"推論 {inference_id} の評価中にエラーが発生しました: {str(e)}", exc_info=True)
        
        # エラーの詳細情報を取得
        error_message = str(e)
        error_type = e.__class__.__name__
        
        # エラー発生場所の特定を試みる
        error_context = ""
        try:
            tb = traceback.extract_tb(e.__traceback__)
            if tb:
                last_frame = tb[-1]
                error_context = f"{last_frame.filename}の{last_frame.name}関数({last_frame.lineno}行目)"
        except:
            pass
        
        # エラー時は推論のステータスを失敗に更新（詳細なエラー情報付き）
        detailed_error = f"エラー: {error_type} - {error_message}"
        if error_context:
            detailed_error += f"\n場所: {error_context}"
        
        inference_repo.update_inference(inference_id, {
            "status": InferenceStatus.FAILED,
            "error": detailed_error
        })


@router.get("/{inference_id}", response_model=Inference)
async def get_inference(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を取得します。
    
    Args:
        inference_id: 推論ID
        
    Returns:
        Inference: 推論情報
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 結果を変換
        results = []
        for res in inference_db.get("results", []):
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            ))
        
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(inference_db["created_at"]) if isinstance(inference_db["created_at"], str) else inference_db["created_at"]
        updated_at = datetime.fromisoformat(inference_db["updated_at"]) if isinstance(inference_db["updated_at"], str) else inference_db["updated_at"]
        completed_at = None
        if inference_db.get("completed_at"):
            completed_at = datetime.fromisoformat(inference_db["completed_at"]) if isinstance(inference_db["completed_at"], str) else inference_db["completed_at"]
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=inference_db["id"],
            name=inference_db["name"],
            description=inference_db.get("description"),
            dataset_id=inference_db["dataset_id"],
            provider_id=inference_db["provider_id"],
            model_id=inference_db["model_id"],
            status=InferenceStatus(inference_db["status"]),
            progress=inference_db["progress"],
            metrics=inference_db.get("metrics"),
            results=results,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error=inference_db.get("error")
        )
        
        return inference
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論取得エラー: {str(e)}"
        )


@router.put("/{inference_id}", response_model=Inference)
async def update_inference(
    inference_data: InferenceUpdate,
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を更新します。
    
    Args:
        inference_id: 更新する推論のID
        inference_data: 更新データ
        
    Returns:
        Inference: 更新された推論情報
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 更新データを準備
        update_data = inference_data.dict(exclude_unset=True)
        
        # 更新を実行
        updated_inference = inference_repo.update_inference(inference_id, update_data)
        
        if not updated_inference:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="推論の更新に失敗しました"
            )
        
        # 結果を変換
        results = []
        for res in updated_inference.get("results", []):
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            ))
        
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(updated_inference["created_at"]) if isinstance(updated_inference["created_at"], str) else updated_inference["created_at"]
        updated_at = datetime.fromisoformat(updated_inference["updated_at"]) if isinstance(updated_inference["updated_at"], str) else updated_inference["updated_at"]
        completed_at = None
        if updated_inference.get("completed_at"):
            completed_at = datetime.fromisoformat(updated_inference["completed_at"]) if isinstance(updated_inference["completed_at"], str) else updated_inference["completed_at"]
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=updated_inference["id"],
            name=updated_inference["name"],
            description=updated_inference.get("description"),
            dataset_id=updated_inference["dataset_id"],
            provider_id=updated_inference["provider_id"],
            model_id=updated_inference["model_id"],
            status=InferenceStatus(updated_inference["status"]),
            progress=updated_inference["progress"],
            metrics=updated_inference.get("metrics"),
            results=results,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error=updated_inference.get("error")
        )
        
        return inference
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論更新エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論更新エラー: {str(e)}"
        )


@router.delete("/{inference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inference(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を削除します。
    
    Args:
        inference_id: 削除する推論のID
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 削除を実行
        success = inference_repo.delete_inference(inference_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="推論の削除に失敗しました"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論削除エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論削除エラー: {str(e)}"
        )


@router.post("/{inference_id}/run", response_model=Inference)
async def run_inference(
    background_tasks: BackgroundTasks,
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を実行します。
    
    Args:
        inference_id: 実行する推論のID
        background_tasks: バックグラウンドタスク
        
    Returns:
        Inference: 実行結果の推論情報
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 現在のステータスをチェック
        if inference_db["status"] == InferenceStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="推論は既に実行中です"
            )
        
        # プロバイダとモデル情報の取得
        provider_repo = get_provider_repository()
        model_repo = get_model_repository()
        
        provider = provider_repo.get_provider_by_id(inference_db["provider_id"])
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダID '{inference_db['provider_id']}' が見つかりません"
            )
        
        model = model_repo.get_model_by_id(inference_db["model_id"])
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{inference_db['model_id']}' が見つかりません"
            )
        
        # パラメータを取得
        parameters = inference_db.get("parameters", {})
        
        # データセット名を抽出
        dataset_name = inference_db["dataset_id"].split('/')[-1].replace('.json', '')
        
        # モデル設定を構築
        model_config = ModelConfig(
            provider=provider["type"],
            model_name=model["name"],
            max_tokens=parameters.get("max_tokens", 512),
            temperature=parameters.get("temperature", 0.7),
            top_p=parameters.get("top_p", 1.0)
        )
        
        # 評価リクエストを構築
        evaluation_request = EvaluationRequest(
            datasets=[dataset_name],
            num_samples=parameters.get("num_samples", 100),
            n_shots=[parameters.get("n_shots", 0)],
            model=model_config
        )
        
        # 推論のステータスを更新
        inference_repo.update_inference(inference_id, {
            "status": InferenceStatus.PENDING,
            "progress": 0,
            "error": None
        })
        
        # 背景タスクで評価を実行
        background_tasks.add_task(
            execute_inference_evaluation,
            inference_id=inference_id,
            evaluation_request=evaluation_request,
            provider_name=provider["type"],
            model_name=model["name"]
        )
        
        # 更新された推論を取得
        updated_inference = inference_repo.get_inference_by_id(inference_id)
        
        # 結果を変換
        results = []
        for res in updated_inference.get("results", []):
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            ))
        
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(updated_inference["created_at"]) if isinstance(updated_inference["created_at"], str) else updated_inference["created_at"]
        updated_at = datetime.fromisoformat(updated_inference["updated_at"]) if isinstance(updated_inference["updated_at"], str) else updated_inference["updated_at"]
        completed_at = None
        if updated_inference.get("completed_at"):
            completed_at = datetime.fromisoformat(updated_inference["completed_at"]) if isinstance(updated_inference["completed_at"], str) else updated_inference["completed_at"]
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=updated_inference["id"],
            name=updated_inference["name"],
            description=updated_inference.get("description"),
            dataset_id=updated_inference["dataset_id"],
            provider_id=updated_inference["provider_id"],
            model_id=updated_inference["model_id"],
            status=InferenceStatus(updated_inference["status"]),
            progress=updated_inference["progress"],
            metrics=updated_inference.get("metrics"),
            results=results,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error=updated_inference.get("error")
        )
        
        return inference
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論実行エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論実行エラー: {str(e)}"
        )


@router.get("/{inference_id}/results", response_model=List[InferenceResult])
async def get_inference_results(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論の結果一覧を取得します。
    
    Args:
        inference_id: 推論ID
        
    Returns:
        List[InferenceResult]: 推論結果一覧
    """
    try:
        # リポジトリから推論を取得（存在チェック）
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 推論結果を取得
        results_db = inference_repo.get_inference_results(inference_id)
        
        # API応答モデルにマッピング
        results = []
        for res in results_db:
            # 日付文字列をdatetimeに変換
            created_at = datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=created_at
            ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論結果取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論結果取得エラー: {str(e)}"
        )