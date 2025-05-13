"""
プロキシエンドポイント
内部サービス（MLflow）へのアクセスをAPIを経由して行うためのエンドポイント
"""
from fastapi import APIRouter, Request, Response, HTTPException
import httpx
from starlette.responses import StreamingResponse
import os
from typing import Optional, List, Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger("llmeval")

# MLflow接続URLの設定（複数の候補から有効なものを選択）
MLFLOW_BASE_URLS = [
    os.environ.get("MLFLOW_HOST_URI"),                # 内部接続用URI（バックエンドからMLflowコンテナへ）
    "http://llm-mlflow-tracking:5000",                # Dockerネットワーク内部でのコンテナ名
    os.environ.get("MLFLOW_EXTERNAL_URI"),            # 外部接続用URI (全システム共通の外部URL)
    "http://localhost:5001"                           # ローカル開発用のURI（フォールバック）
]

# 後方互換性のためのフォールバック処理(必要に応じて削除可)
if os.environ.get("LLMEVAL_MLFLOW_EXTERNAL_URI") and not os.environ.get("MLFLOW_EXTERNAL_URI"):
    MLFLOW_BASE_URLS.append(os.environ.get("LLMEVAL_MLFLOW_EXTERNAL_URI"))
    logger.info(f"LLMEVAL_MLFLOW_EXTERNAL_URIが設定されていますが、MLFLOW_EXTERNAL_URIへの移行を推奨します")

# 空の値をフィルタリング
MLFLOW_BASE_URLS = [url for url in MLFLOW_BASE_URLS if url]

# ログ出力
logger.info(f"MLflow接続候補: {MLFLOW_BASE_URLS}")

# 最初の有効な接続先を使用
MLFLOW_BASE_URL = MLFLOW_BASE_URLS[0] if MLFLOW_BASE_URLS else "http://llm-mlflow-tracking:5000"
logger.info(f"選択されたMLflow接続先: {MLFLOW_BASE_URL}")


@router.get("/proxy-mlflow/{path:path}")
@router.post("/proxy-mlflow/{path:path}")
@router.put("/proxy-mlflow/{path:path}")
@router.delete("/proxy-mlflow/{path:path}")
async def proxy_mlflow(request: Request, path: str):
    """
    MLflowサーバーへのリクエストをプロキシする
    複数の接続先を試し、最初に成功した接続を使用する
    """
    # リクエストボディと全てのクエリパラメータ・ヘッダーを転送
    body = await request.body()

    # 設定されているMLflow URLを順番に試す
    for base_url in [url for url in MLFLOW_BASE_URLS if url]:
        target_url = f"{base_url}/{path}"
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
            continue  # 次のURLを試す

    # すべてのURLが失敗した場合
    logger.error(f"All MLflow proxy attempts failed for path: {path}")
    raise HTTPException(
        status_code=503,
        detail=f"Failed to connect to MLflow server. Please check if the service is running."
    )

# MLflowルートパスへのプロキシ
@router.get("/proxy-mlflow/")
@router.post("/proxy-mlflow/")
@router.put("/proxy-mlflow/")
@router.delete("/proxy-mlflow/")
async def proxy_mlflow_root(request: Request):
    """
    MLflowサーバーのルートパスへのリクエストをプロキシする
    """
    return await proxy_mlflow(request, "")

# MLflowの状態確認エンドポイント
@router.get("/mlflow-status")
async def mlflow_status():
    """
    MLflowサーバーの状態を確認する
    """
    status = {
        "mlflow_urls": [url for url in MLFLOW_BASE_URLS if url],
        "status": "unknown",
        "details": {}
    }

    for i, base_url in enumerate([url for url in MLFLOW_BASE_URLS if url]):
        try:
            logger.info(f"Checking MLflow status at: {base_url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(base_url, timeout=5.0)
                status["details"][f"url_{i}"] = {
                    "url": base_url,
                    "status_code": response.status_code,
                    "ok": response.status_code < 400
                }
                if response.status_code < 400:
                    status["status"] = "ok"
        except Exception as e:
            status["details"][f"url_{i}"] = {
                "url": base_url,
                "error": str(e),
                "ok": False
            }

    # すべてのURLが失敗した場合
    if status["status"] == "unknown":
        status["status"] = "error"

    return status