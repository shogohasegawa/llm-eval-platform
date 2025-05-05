"""
プロバイダー管理APIエンドポイント

プロバイダーのCRUD操作を提供するエンドポイントを実装します。
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from app.api.api_schemas import Provider, ProviderCreate, ProviderUpdate
from app.utils.db.providers import get_provider_repository

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.post("", response_model=Provider, status_code=status.HTTP_201_CREATED)
async def create_provider(provider_data: ProviderCreate):
    """
    新しいプロバイダーを作成します。
    
    Args:
        provider_data: 作成するプロバイダーのデータ
        
    Returns:
        作成されたプロバイダー情報
    """
    provider_repo = get_provider_repository()
    
    try:
        provider = provider_repo.create_provider(provider_data.model_dump())
        return provider
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プロバイダー作成エラー: {str(e)}"
        )


@router.get("", response_model=List[Provider])
async def get_all_providers():
    """
    すべてのプロバイダーを取得します。
    
    Returns:
        プロバイダーのリスト
    """
    provider_repo = get_provider_repository()
    
    try:
        providers = provider_repo.get_all_providers()
        return providers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プロバイダー取得エラー: {str(e)}"
        )


@router.get("/{provider_id}", response_model=Provider)
async def get_provider(provider_id: str):
    """
    特定のプロバイダーを取得します。
    
    Args:
        provider_id: プロバイダーID
        
    Returns:
        プロバイダー情報
    """
    provider_repo = get_provider_repository()
    
    try:
        provider = provider_repo.get_provider_by_id(provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダーID '{provider_id}' が見つかりません"
            )
        return provider
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プロバイダー取得エラー: {str(e)}"
        )


@router.put("/{provider_id}", response_model=Provider)
async def update_provider(provider_id: str, provider_data: ProviderUpdate):
    """
    特定のプロバイダーを更新します。
    
    Args:
        provider_id: 更新するプロバイダーのID
        provider_data: 更新データ
        
    Returns:
        更新されたプロバイダー情報
    """
    provider_repo = get_provider_repository()
    
    try:
        # 更新データから None 以外のフィールドのみを抽出
        update_data = {k: v for k, v in provider_data.model_dump().items() if v is not None}
        
        provider = provider_repo.update_provider(provider_id, update_data)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダーID '{provider_id}' が見つかりません"
            )
        return provider
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プロバイダー更新エラー: {str(e)}"
        )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(provider_id: str):
    """
    特定のプロバイダーを削除します。
    
    Args:
        provider_id: 削除するプロバイダーのID
    """
    provider_repo = get_provider_repository()
    
    try:
        success = provider_repo.delete_provider(provider_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダーID '{provider_id}' が見つかりません"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プロバイダー削除エラー: {str(e)}"
        )
