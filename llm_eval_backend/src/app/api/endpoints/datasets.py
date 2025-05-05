"""
データセットAPI

データセットの登録、一覧取得、詳細取得などのエンドポイントを提供
"""
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Path as PathParam, Query, status, UploadFile, File, Form
from app.api.models import (
    DatasetListResponse, 
    DatasetDetailResponse,
    DatasetDeleteResponse,
    DatasetItem
)
from app.utils.dataset.operations import (
    get_datasets_list,
    get_dataset_by_name,
    get_dataset_by_path,
    delete_dataset,
    save_json_file
)
from app.config.config import get_settings

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("/upload", response_model=DatasetDetailResponse)
async def upload_dataset_file(
    file: UploadFile = File(...),
    dataset_type: str = Form(..., description="データセットタイプ: 'test' または 'n_shot'")
):
    """
    JSONファイルからデータセットをアップロードする
    
    Args:
        file: アップロードするJSONファイル
        dataset_type: データセットタイプ ('test' または 'n_shot')
        
    Returns:
        DatasetDetailResponse: アップロードされたデータセット情報
    """
    # ファイル形式のチェック
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JSONファイルのみアップロード可能です。"
        )
    
    # データセットタイプのチェック
    if dataset_type not in ["test", "n_shot"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="データセットタイプは 'test' または 'n_shot' である必要があります。"
        )
    
    try:
        # ファイルの読み込み
        content = await file.read()
        file_content = content.decode("utf-8")
        
        # JSONとしてパース
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なJSON形式です。"
            )
        
        # ファイル名から拡張子を除いた部分をデータセット名として使用
        dataset_name = os.path.splitext(file.filename)[0]
        
        # ファイルの保存
        file_path = save_json_file(dataset_name, data, dataset_type)
        
        logger.info(f"JSONファイルからデータセットを保存しました: {file_path}")
        
        # 保存されたデータセットの情報を取得
        saved_dataset = get_dataset_by_path(str(file_path))
        
        if not saved_dataset:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="データセットの保存に成功しましたが、読み込みに失敗しました。"
            )
        
        return DatasetDetailResponse(
            metadata=saved_dataset["metadata"],
            items=saved_dataset["items"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSONファイルからのデータセットアップロードに失敗しました: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"データセットアップロードに失敗しました: {str(e)}"
        )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(type: Optional[str] = Query(None, description="データセットタイプでフィルタ ('test' または 'n_shot')")):
    """
    利用可能なデータセットの一覧を取得
    
    Args:
        type: データセットタイプでフィルタ (オプション)
        
    Returns:
        DatasetListResponse: データセットメタデータのリスト
    """
    try:
        datasets = get_datasets_list()
        
        # タイプが指定されている場合はフィルタリング
        if type:
            if type not in ["test", "n_shot"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="無効なデータセットタイプです。'test' または 'n_shot' を指定してください。"
                )
            datasets = [d for d in datasets if d.type == type]
        
        return DatasetListResponse(datasets=datasets)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"データセット一覧の取得に失敗しました: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"データセット一覧の取得に失敗しました: {str(e)}"
        )


@router.get("/{name}", response_model=DatasetDetailResponse)
async def get_dataset_detail(
    name: str = PathParam(..., description="データセット名")
):
    """
    データセットの詳細情報を取得
    
    Args:
        name: データセット名
        
    Returns:
        DatasetDetailResponse: データセットの詳細情報
    """
    try:
        dataset = get_dataset_by_name(name)
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"データセット '{name}' が見つかりません。"
            )
        
        return DatasetDetailResponse(
            metadata=dataset["metadata"],
            items=dataset["items"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"データセット詳細の取得に失敗しました: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"データセット詳細の取得に失敗しました: {str(e)}"
        )


@router.delete("/by-path", response_model=DatasetDeleteResponse)
async def delete_dataset_by_path(
    file_path: str = Query(..., description="削除するデータセットファイルのパス")
):
    """
    データセットを削除
    
    Args:
        file_path: 削除するデータセットファイルのパス
        
    Returns:
        DatasetDeleteResponse: 削除結果
    """
    try:
        # データセットの存在確認
        dataset = get_dataset_by_path(file_path)
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"指定されたパスのデータセットが見つかりません: {file_path}"
            )
        
        # データセットの削除
        success = delete_dataset(file_path)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="データセットの削除に失敗しました。"
            )
        
        return DatasetDeleteResponse(
            success=True,
            message=f"データセット '{dataset['metadata'].name}' を削除しました。"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"データセットの削除に失敗しました: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"データセットの削除に失敗しました: {str(e)}"
        )
