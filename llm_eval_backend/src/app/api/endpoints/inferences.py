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
from app.core.evaluation import run_multiple_evaluations
from app.utils.litellm_helper import get_provider_options

# ロガーの設定
logger = logging.getLogger("llmeval")

router = APIRouter(prefix="/api/inferences", tags=["inferences"])


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
    # 実際のデータベース実装があれば、ここでクエリを実行する
    # 今回はモックデータを返す
    return []


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
        
        # プロバイダとモデル情報の取得（実際のDBから取得する実装ができたらここを修正）
        provider_type = "ollama"  # 本来はDBから取得
        model_name = "gpt4"       # 本来はDBから取得
        
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
        
        # 評価の実行（同期）
        # リクエストからモデル情報と追加パラメータを取得
        provider_name = model_config.provider
        model_name = model_config.model_name
        
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
        
        # 新しい推論を作成
        now = datetime.now()
        inference_id = str(uuid.uuid4())
        
        # 推論結果を作成（実際のデータがあればここで設定）
        results = []
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=inference_id,
            name=inference_data.name,
            description=inference_data.description,
            dataset_id=inference_data.dataset_id,
            provider_id=inference_data.provider_id,
            model_id=inference_data.model_id,
            status=InferenceStatus.COMPLETED,
            progress=100,
            metrics=flat_metrics,
            results=results,
            created_at=now,
            updated_at=now,
            completed_at=now
        )
        
        return inference
        
    except Exception as e:
        logger.error(f"推論作成エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論作成エラー: {str(e)}"
        )


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
    # 実際のデータベース実装があれば、ここでクエリを実行する
    # 今回はモックデータを返す
    return None


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
    # 実際のデータベース実装があれば、ここでクエリを実行する
    # 今回はモックデータを返す
    return None


@router.delete("/{inference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inference(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を削除します。
    
    Args:
        inference_id: 削除する推論のID
    """
    # 実際のデータベース実装があれば、ここでクエリを実行する
    pass


@router.post("/{inference_id}/run", response_model=Inference)
async def run_inference(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を実行します。
    
    Args:
        inference_id: 実行する推論のID
        
    Returns:
        Inference: 実行結果の推論情報
    """
    # 実際のデータベース実装があれば、ここでクエリを実行する
    # 今回はモックデータを返す
    return None


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
    # 実際のデータベース実装があれば、ここでクエリを実行する
    # 今回はモックデータを返す
    return []