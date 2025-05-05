"""
モデル管理APIエンドポイント

モデルのCRUD操作を提供するエンドポイントを実装します。
"""
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel

from app.api.api_schemas import Model, ModelCreate, ModelUpdate
from app.utils.db.models import get_model_repository
from app.utils.db.providers import get_provider_repository
from app.utils.litellm_helper import update_router_model

# ロガーの設定
logger = logging.getLogger("llmeval")

router = APIRouter(prefix="/api/models", tags=["models"])


@router.post("", response_model=Model, status_code=status.HTTP_201_CREATED)
async def create_model(request: Request, model_data: ModelCreate):
    """
    新しいモデルを作成します。
    
    Args:
        request: リクエストオブジェクト
        model_data: 作成するモデルのデータ
        
    Returns:
        作成されたモデル情報
    """
    # リクエストボディの生データを取得
    body = await request.body()
    logger.info(f"受信リクエストボディ (raw): {body.decode('utf-8')}")
    
    # デバッグ用ログ
    logger.info(f"モデル作成リクエスト受信: {model_data}")
    logger.info(f"リクエストデータ(model_dump): {model_data.model_dump()}")
    logger.info(f"リクエストデータ(dict): {dict(model_data)}")
    
    model_repo = get_model_repository()
    provider_repo = get_provider_repository()
    
    # プロバイダーが存在するか確認
    provider = provider_repo.get_provider_by_id(model_data.provider_id)
    if not provider:
        logger.error(f"プロバイダーIDエラー: '{model_data.provider_id}' が見つかりません")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"プロバイダーID '{model_data.provider_id}' が見つかりません"
        )
    
    try:
        # リクエストデータをダンプしてログ出力
        model_dump = model_data.model_dump()
        logger.info(f"モデルデータ変換後: {model_dump}")
        
        # モデルをデータベースに登録
        model = model_repo.create_model(model_dump)
        logger.info(f"モデル作成成功: {model}")
        
        # モデルが有効な場合は、LiteLLM Routerを更新
        if model.get("is_active", False):
            logger.info(f"LiteLLM Routerにモデルを追加: {model['name']}")
            update_router_model(model)
        
        return model
    except ValueError as e:
        logger.error(f"モデル作成バリデーションエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"モデル作成エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"モデル作成エラー: {str(e)}"
        )


@router.get("", response_model=List[Model])
async def get_all_models():
    """
    すべてのモデルを取得します。
    
    Returns:
        モデルのリスト
    """
    model_repo = get_model_repository()
    
    try:
        models = model_repo.get_all_models()
        return models
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"モデル取得エラー: {str(e)}"
        )


@router.get("/by-provider/{provider_id}", response_model=List[Model])
async def get_models_by_provider(provider_id: str):
    """
    特定のプロバイダーに属するモデルを取得します。
    
    Args:
        provider_id: プロバイダーID
        
    Returns:
        モデルのリスト
    """
    model_repo = get_model_repository()
    provider_repo = get_provider_repository()
    
    # プロバイダーが存在するか確認
    provider = provider_repo.get_provider_by_id(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"プロバイダーID '{provider_id}' が見つかりません"
        )
    
    try:
        models = model_repo.get_models_by_provider(provider_id)
        return models
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"モデル取得エラー: {str(e)}"
        )


@router.get("/{model_id}", response_model=Model)
async def get_model(model_id: str):
    """
    特定のモデルを取得します。
    
    Args:
        model_id: モデルID
        
    Returns:
        モデル情報
    """
    model_repo = get_model_repository()
    
    try:
        model = model_repo.get_model_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{model_id}' が見つかりません"
            )
        return model
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"モデル取得エラー: {str(e)}"
        )


@router.put("/{model_id}", response_model=Model)
async def update_model(model_id: str, model_data: ModelUpdate):
    """
    特定のモデルを更新します。
    
    Args:
        model_id: 更新するモデルのID
        model_data: 更新データ
        
    Returns:
        更新されたモデル情報
    """
    model_repo = get_model_repository()
    provider_repo = get_provider_repository()
    
    # プロバイダーIDが指定されている場合、存在チェック
    if model_data.provider_id:
        provider = provider_repo.get_provider_by_id(model_data.provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダーID '{model_data.provider_id}' が見つかりません"
            )
    
    try:
        # 更新データから None 以外のフィールドのみを抽出
        update_data = {k: v for k, v in model_data.model_dump().items() if v is not None}
        
        # モデルをデータベースで更新
        model = model_repo.update_model(model_id, update_data)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{model_id}' が見つかりません"
            )
        
        # LiteLLM Routerを更新
        logger.info(f"LiteLLM Routerのモデル情報を更新: {model['name']}")
        update_router_model(model)
        
        return model
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"モデル更新エラー: {str(e)}"
        )


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: str):
    """
    特定のモデルを削除します。
    
    Args:
        model_id: 削除するモデルのID
    """
    model_repo = get_model_repository()
    
    try:
        # 削除前にモデル情報を取得
        model = model_repo.get_model_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{model_id}' が見つかりません"
            )
        
        # モデルを削除
        success = model_repo.delete_model(model_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{model_id}' が見つかりません"
            )
        
        # このモデルを使用しているLiteLLM Routerの設定を更新
        # 注：モデル削除時はルーターの更新が必要な場合は、ルーターの再初期化が適切かも
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"モデル削除エラー: {str(e)}"
        )
