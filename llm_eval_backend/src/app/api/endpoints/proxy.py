"""
プロキシエンドポイント
内部サービス（MLflow, Ollama）へのアクセスをAPIを経由して行うためのエンドポイント
"""
from fastapi import APIRouter, Request, Response, HTTPException
import httpx
from starlette.responses import StreamingResponse
import os
from typing import Optional, List, Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger("llmeval")

# プロキシ設定
OLLAMA_BASE_URLS = [
    os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
    os.environ.get("OLLAMA_EXTERNAL_URL", "")
]

MLFLOW_BASE_URL = os.environ.get("MLFLOW_HOST_URI", "http://mlflow:5000")

@router.get("/proxy-ollama/{path:path}")
@router.post("/proxy-ollama/{path:path}")
@router.put("/proxy-ollama/{path:path}")
@router.delete("/proxy-ollama/{path:path}")
async def proxy_ollama(request: Request, path: str):
    """
    Ollamaサーバーへのリクエストをプロキシする
    複数の接続先を試し、最初に成功した接続を使用する
    """
    # リクエストボディと全てのクエリパラメータ・ヘッダーを転送
    body = await request.body()
    
    # 設定されているOllama URLを順番に試す
    for base_url in [url for url in OLLAMA_BASE_URLS if url]:
        target_url = f"{base_url}/{path}"
        logger.info(f"Proxying Ollama request to: {target_url}")
        
        try:
            async with httpx.AsyncClient() as client:
                # リクエストヘッダーをコピーするが、ホストヘッダーは除外
                headers = dict(request.headers)
                headers.pop("host", None)
                
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    content=body,
                    headers=headers,
                    params=dict(request.query_params),
                    timeout=60.0
                )
                
                # レスポンスヘッダーをコピー（Content-Lengthなどの特定ヘッダーは除外）
                resp_headers = dict(response.headers)
                resp_headers.pop("content-length", None)
                resp_headers.pop("transfer-encoding", None)
                
                # ストリーミングレスポンスの場合
                if "content-type" in resp_headers and "stream" in resp_headers.get("content-type", ""):
                    return StreamingResponse(
                        response.aiter_bytes(),
                        status_code=response.status_code,
                        headers=resp_headers
                    )
                
                # 通常のレスポンス
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=resp_headers
                )
        except Exception as e:
            logger.error(f"Error proxying to {target_url}: {e}")
            continue
    
    # すべてのURLが失敗した場合
    logger.error(f"All Ollama proxy attempts failed for path: {path}")
    raise HTTPException(
        status_code=503,
        detail=f"Failed to connect to Ollama server. Please check if the service is running."
    )

# ルートパスへのプロキシ（/proxy-ollama/ -> http://ollama:11434/）
@router.get("/proxy-ollama/")
@router.post("/proxy-ollama/")
async def proxy_ollama_root(request: Request):
    """
    Ollamaサーバーのルートパスへのリクエストをプロキシする
    """
    return await proxy_ollama(request, "")

@router.get("/proxy-mlflow/{path:path}")
@router.post("/proxy-mlflow/{path:path}")
@router.put("/proxy-mlflow/{path:path}")
@router.delete("/proxy-mlflow/{path:path}")
async def proxy_mlflow(request: Request, path: str):
    """
    MLflowサーバーへのリクエストをプロキシする
    """
    # リクエストボディと全てのクエリパラメータ・ヘッダーを転送
    body = await request.body()
    target_url = f"{MLFLOW_BASE_URL}/{path}"
    
    logger.info(f"Proxying MLflow request to: {target_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            # リクエストヘッダーをコピーするが、ホストヘッダーは除外
            headers = dict(request.headers)
            headers.pop("host", None)
            
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                params=dict(request.query_params),
                timeout=60.0
            )
            
            # レスポンスヘッダーをコピー（Content-Lengthなどの特定ヘッダーは除外）
            resp_headers = dict(response.headers)
            resp_headers.pop("content-length", None)
            resp_headers.pop("transfer-encoding", None)
            
            # 通常のレスポンス
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=resp_headers
            )
    except Exception as e:
        logger.error(f"Error proxying to MLflow {target_url}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to MLflow server: {str(e)}"
        )

# MLflowルートパスへのプロキシ
@router.get("/proxy-mlflow/")
@router.post("/proxy-mlflow/")
async def proxy_mlflow_root(request: Request):
    """
    MLflowサーバーのルートパスへのリクエストをプロキシする
    """
    return await proxy_mlflow(request, "")