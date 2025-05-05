"""
API初期化モジュール
"""
from fastapi import APIRouter

# ルーターのインポート（絶対パスで明示的にインポート）
from app.api.endpoints.db_models import router as db_models_router
from app.api.endpoints.datasets import router as datasets_router
from app.api.endpoints.evaluation import router as evaluation_router
from app.api.endpoints.providers import router as providers_router
from app.api.endpoints.inferences import router as inferences_router

# メインルーター
api_router = APIRouter()

# 各ルーターをメインルーターに追加
api_router.include_router(db_models_router)
api_router.include_router(datasets_router)
api_router.include_router(evaluation_router)
api_router.include_router(providers_router)
api_router.include_router(inferences_router)
