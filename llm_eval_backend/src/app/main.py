import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.api import api_router
from app.utils.db import get_db
from app.utils.app_logging import setup_logging

# ロギングの設定
log_level = os.environ.get("LLMEVAL_LOG_LEVEL", "INFO")
setup_logging(log_level=log_level)
logger = logging.getLogger("llmeval")

app = FastAPI(title="LLM Evaluation API")

# CORS設定（React Appとの連携用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に設定する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース接続の初期化
db = get_db()

# APIルーターを追加
app.include_router(api_router, prefix="/api")

# リクエスト・レスポンスのロギング
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"リクエスト受信: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        logger.debug(f"レスポンス送信: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"リクエスト処理エラー: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )

# エラーハンドリング
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    logger.error(f"バリデーションエラー: {exc.detail}")
    return JSONResponse(
        status_code=422,
        content={"detail": "リクエストのバリデーションに失敗しました。", "errors": exc.detail}
    )

# アプリ起動イベント
@app.on_event("startup")
async def startup_event():
    # アプリケーション起動時に実行する処理
    logger.info("アプリケーション起動中...")
    
    # LiteLLMキャッシュの初期化
    from app.utils.litellm_helper import init_litellm_cache
    init_litellm_cache()
    
    # LiteLLM Routerの初期化
    from app.utils.litellm_helper import init_router_from_db
    logger.info("LiteLLM Routerを初期化中...")
    init_router_from_db()
    logger.info("LiteLLM Router初期化完了")
    
    logger.info("アプリケーション起動完了")

# アプリ終了イベント    
@app.on_event("shutdown")
async def shutdown_event():
    # アプリケーション終了時に実行する処理
    logger.info("アプリケーション終了中...")
    
    # データベース接続のクローズなど
    db.close()
    
    logger.info("アプリケーション終了完了")

# ルートエンドポイント
@app.get("/")
async def root():
    logger.debug("ルートエンドポイントへのアクセス")
    return {"message": "LLM Evaluation Platform API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
