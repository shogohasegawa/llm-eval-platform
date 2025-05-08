"""
Ollama管理APIエンドポイント

Ollamaモデルのダウンロードを管理するエンドポイントを実装します。
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel

from app.utils.ollama_manager import get_ollama_manager, DownloadStatus
from app.utils.db.models import get_model_repository
from app.utils.db.providers import get_provider_repository

# ロガーの設定
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ollama", tags=["ollama"])


class OllamaModelDownloadRequest(BaseModel):
    """Ollamaモデルダウンロードリクエスト"""
    model_id: str
    model_name: str
    endpoint: Optional[str] = None


class OllamaModelDownloadResponse(BaseModel):
    """Ollamaモデルダウンロードレスポンス"""
    download_id: str
    model_id: str
    model_name: str
    status: DownloadStatus
    progress: int
    endpoint: str


class OllamaModelDownloadDetailResponse(BaseModel):
    """Ollamaモデルダウンロード詳細レスポンス"""
    id: str
    model_id: str
    model_name: str
    endpoint: str
    status: DownloadStatus
    progress: int
    total_size: int  # ダウンロード時の転送サイズ (バイト単位)
    downloaded_size: int  # ダウンロード済みの転送サイズ (バイト単位)
    model_size: int = 0  # モデルの実際のサイズ (バイト単位)
    model_size_gb: float = 0.0  # モデルの実際のサイズ (GB単位)
    error: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    digest: Optional[str] = None
    model_info: Optional[dict] = None  # モデルの詳細情報


@router.post("/download", response_model=OllamaModelDownloadResponse)
async def download_ollama_model(request: OllamaModelDownloadRequest):
    """
    Ollamaモデルのダウンロードを開始します。
    
    Args:
        request: ダウンロードリクエスト
        
    Returns:
        ダウンロード情報
    """
    model_repo = get_model_repository()
    provider_repo = get_provider_repository()
    
    try:
        # モデルが存在するか確認
        model = model_repo.get_model_by_id(request.model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{request.model_id}' が見つかりません"
            )
        
        # プロバイダーがollamaかどうか確認
        provider = provider_repo.get_provider_by_id(model["provider_id"])
        if not provider or provider["type"].lower() != "ollama":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"モデル '{model['name']}' はOllamaプロバイダではありません"
            )
        
        # エンドポイントの取得（リクエスト > モデル > プロバイダの順）
        endpoint = request.endpoint
        if not endpoint:
            endpoint = model.get("endpoint")
        if not endpoint:
            endpoint = provider.get("endpoint")
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ollamaエンドポイントが指定されていません"
            )
        
        # デフォルトのOllamaエンドポイント
        if endpoint == "ollama":
            endpoint = "http://localhost:11434"
            
        # エンドポイントがURLパスを含む場合は削除（ベースURLのみ使用）
        if '/api/' in endpoint:
            # /api/ より前の部分だけを取得
            endpoint = endpoint.split('/api/')[0]
        
        # プロトコルが含まれていることを確認
        if not endpoint.startswith(('http://', 'https://')):
            endpoint = f"http://{endpoint}"
        
        # Ollamaマネージャの取得とダウンロード開始
        ollama_manager = get_ollama_manager()
        download_info = await ollama_manager.download_model(
            model_name=request.model_name, 
            model_id=request.model_id,
            endpoint=endpoint
        )
        
        # レスポンスを作成
        return {
            "download_id": download_info["id"],
            "model_id": download_info["model_id"],
            "model_name": download_info["model_name"],
            "status": download_info["status"],
            "progress": download_info["progress"],
            "endpoint": download_info["endpoint"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ollamaモデルダウンロード開始エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollamaモデルダウンロード開始エラー: {str(e)}"
        )


@router.get("/download/{download_id}", response_model=OllamaModelDownloadDetailResponse)
async def get_download_status(download_id: str):
    """
    ダウンロードステータスを取得します。
    
    Args:
        download_id: ダウンロードID
        
    Returns:
        ダウンロード詳細情報
    """
    ollama_manager = get_ollama_manager()
    
    try:
        logger.info(f"[OLLAMA_API] ダウンロードステータス取得リクエスト: ID={download_id}")
        download_info = ollama_manager.get_download(download_id)
        
        if not download_info:
            logger.warning(f"[OLLAMA_API] ダウンロードIDが見つかりません: {download_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ダウンロードID '{download_id}' が見つかりません"
            )
        
        # 返却前にステータス情報をログ出力
        status_value = download_info.get("status", "unknown")
        error_value = download_info.get("error")
        progress_value = download_info.get("progress", 0)
        model_name = download_info.get("model_name", "unknown")
        
        logger.info(f"[OLLAMA_API] ダウンロードステータス応答: ID={download_id}, モデル={model_name}, ステータス={status_value}, 進捗={progress_value}%, エラー={error_value}")
        
        return download_info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ダウンロードステータス取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ダウンロードステータス取得エラー: {str(e)}"
        )


@router.get("/downloads/model/{model_id}", response_model=List[OllamaModelDownloadDetailResponse])
async def get_downloads_by_model(model_id: str):
    """
    特定のモデルのダウンロード履歴を取得します。
    
    Args:
        model_id: モデルID
        
    Returns:
        ダウンロード情報のリスト
    """
    model_repo = get_model_repository()
    ollama_manager = get_ollama_manager()
    
    try:
        # モデルが存在するか確認
        model = model_repo.get_model_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{model_id}' が見つかりません"
            )
        
        # ダウンロード履歴を取得
        downloads = ollama_manager.get_downloads_by_model_id(model_id)
        return downloads
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"モデルダウンロード履歴取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"モデルダウンロード履歴取得エラー: {str(e)}"
        )


@router.get("/downloads", response_model=List[OllamaModelDownloadDetailResponse])
async def get_all_downloads():
    """
    すべてのダウンロード履歴を取得します。
    
    Returns:
        ダウンロード情報のリスト
    """
    ollama_manager = get_ollama_manager()
    
    try:
        downloads = ollama_manager.get_all_downloads()
        return downloads
    
    except Exception as e:
        logger.error(f"ダウンロード履歴取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ダウンロード履歴取得エラー: {str(e)}"
        )


@router.get("/check_model", response_model=Dict[str, Any])
async def check_ollama_model(model_name: str, endpoint: Optional[str] = None):
    """
    Ollamaモデルの存在チェックを行います。
    
    Args:
        model_name: モデル名
        endpoint: Ollamaエンドポイント（オプション）
        
    Returns:
        モデル情報
    """
    import aiohttp
    import json
    
    # エンドポイントのデフォルト値
    if not endpoint:
        endpoint = "http://localhost:11434"
    
    # エンドポイントにプロトコルが含まれていなければ追加
    if not endpoint.startswith(('http://', 'https://')):
        endpoint = f"http://{endpoint}"
    
    # エンドポイントが正しい形式かチェック
    if not endpoint.endswith('/'):
        endpoint = f"{endpoint}/"
    
    api_url = f"{endpoint}api/tags"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollamaモデル情報取得エラー: {error_text}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Ollamaモデル情報取得エラー: HTTP {response.status} - {error_text}"
                    )
                
                data = await response.json()
                
                # モデルが存在するか確認
                for model in data.get("models", []):
                    if model.get("name") == model_name:
                        return {
                            "exists": True,
                            "model_info": model
                        }
                
                # モデルが見つからない場合
                return {
                    "exists": False,
                    "available_models": [m.get("name") for m in data.get("models", [])]
                }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ollamaモデルチェックエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollamaモデルチェックエラー: {str(e)}"
        )