"""
LiteLLM関連のユーティリティ関数とヘルパークラス
"""
import logging
import json
import os
import hashlib
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
import litellm
from litellm import Router
from pydantic import BaseModel
from app.config import get_settings

# 設定の取得
settings = get_settings()
logger = logging.getLogger(__name__)

# モデル情報のグローバルキャッシュ
MODEL_INFO_CACHE = {}

# ルーターインスタンス（シングルトン）
_router_instance = None

def init_litellm_cache():
    """
    LiteLLMのキャッシュを初期化する関数

    キャッシュが有効な場合はLiteLLMのキャッシュを有効化します
    """
    if settings.ENABLE_LITELLM_CACHE:
        logger.info("Initializing LiteLLM cache")
        litellm.cache = litellm.Cache(
            type="redis",
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            ttl=settings.CACHE_EXPIRATION
        )
        logger.info("LiteLLM cache initialized")
    else:
        logger.info("LiteLLM cache is disabled")

def generate_cache_key(messages: List[Dict[str, str]], model: str) -> str:
    """
    キャッシュキーを生成する関数

    Args:
        messages: メッセージのリスト
        model: モデル名

    Returns:
        キャッシュキーの文字列
    """
    # シンプルなキャッシュキー生成
    key_data = {
        "model": model,
        "messages": messages
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()

def check_cache(messages: List[Dict[str, str]], model: str) -> Optional[str]:
    """
    キャッシュをチェックする関数

    Args:
        messages: メッセージのリスト
        model: モデル名

    Returns:
        キャッシュが存在する場合はキャッシュされた出力、そうでない場合はNone
    """
    if not settings.ENABLE_LITELLM_CACHE:
        return None

    key = generate_cache_key(messages, model)

    try:
        cache_path = f"cache/{key}.json"
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Cache hit for key {key}")
                return data.get("content")
    except Exception as e:
        logger.warning(f"Error checking cache: {e}")

    return None

def update_cache(messages: List[Dict[str, str]], model: str, content: str) -> None:
    """
    キャッシュを更新する関数

    Args:
        messages: メッセージのリスト
        model: モデル名
        content: キャッシュする内容
    """
    if not settings.ENABLE_LITELLM_CACHE:
        return

    key = generate_cache_key(messages, model)

    try:
        os.makedirs("cache", exist_ok=True)
        cache_path = f"cache/{key}.json"
        data = {
            "model": model,
            "content": content
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        logger.info(f"Cache updated for key {key}")
    except Exception as e:
        logger.warning(f"Error updating cache: {e}")

def get_provider_options(provider_name: str) -> Dict[str, Any]:
    """
    特定のプロバイダのオプションを取得する関数

    Args:
        provider_name: プロバイダ名

    Returns:
        プロバイダオプションの辞書
    """
    # プロバイダごとの設定を取得
    provider_settings = settings.get_provider_settings(provider_name)

    # プロバイダごとのデフォルトヘッダーやオプションを設定
    default_options = {
        "openai": {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0"
            }
        },
        "anthropic": {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0",
                "anthropic-version": "2023-06-01"
            }
        },
        "ollama": {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0"
            }
        },
        "azure": {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0"
            }
        },
        "cohere": {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0"
            }
        },
        "gemini": {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0"
            }
        },
        "mistral": {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0"
            }
        },
        "together": {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0"
            }
        }
    }

    # プロバイダがサポートされているか確認
    if provider_name not in default_options:
        logger.warning(f"Provider {provider_name} is not directly supported. Using default options.")
        return {
            "headers": {
                "User-Agent": "LLM-Evaluation-Tool/1.0"
            }
        }

    # ベースとなるオプションを取得
    options = default_options.get(provider_name, {}).copy()

    # 設定から追加のパラメータを適用
    if provider_settings:
        # ヘッダーがある場合は更新
        if "headers" in options and "headers" in provider_settings:
            options["headers"].update(provider_settings["headers"])
        # その他の設定を更新
        for key, value in provider_settings.items():
            if key != "headers":
                options[key] = value

    return options


def format_litellm_model_name(provider_name: str, model_name: str) -> str:
    """
    LiteLLM形式のモデル名を生成する関数

    LiteLLMが期待する形式でプロバイダーとモデル名を結合します。

    Args:
        provider_name: プロバイダ名
        model_name: モデル名

    Returns:
        LiteLLM形式のモデル名
    """

    if provider_name != "ollama":
        return model_name


    return f"{provider_name}/{model_name}"

class ModelConfig(BaseModel):
    """モデル設定クラス"""
    model_name: str
    litellm_params: Dict[str, Any]
    alias: Optional[str] = None
    timeout: Optional[int] = None
    weight: Optional[int] = 1

class RouterManager:
    """LiteLLM Routerを管理するクラス"""

    def __init__(self):
        """初期化処理"""
        self.router = None
        self.configs = []
        self.enabled = False

    def initialize(self, configs: List[ModelConfig], routing_strategy: str = "simple-shuffle"):
        """
        ルーターを初期化する

        Args:
            configs: モデル設定のリスト
            routing_strategy: ルーティング戦略
        """
        model_list = []

        for config in configs:
            model_entry = {
                "model_name": config.model_name,
                "litellm_params": {
                    "model": config.model_name,
                    **config.litellm_params,
                    },
            }

            if config.alias:
                model_entry["alias"] = config.alias

            if config.timeout:
                model_entry["timeout"] = config.timeout

            if config.weight:
                model_entry["weight"] = config.weight

            model_list.append(model_entry)

        # ルーターを初期化
        self.router = Router(
            model_list=model_list,
            routing_strategy=routing_strategy,
            fallbacks=[],  # 明示的なフォールバックの有効化はここで設定
            context_window_fallbacks=[],  # コンテキストウィンドウ制限によるフォールバック
            num_retries=settings.MODEL_RETRIES,
            timeout=settings.MODEL_TIMEOUT,
            routing_strategy_args={}
        )

        self.configs = configs
        self.enabled = True
        logger.info(f"Router initialized with {len(configs)} models and strategy '{routing_strategy}'")

    def add_model(self, config: ModelConfig):
        """
        ルーターにモデルを追加する

        Args:
            config: モデル設定
        """
        if not self.router:
            self.initialize([config])
            return

        model_entry = {
            "model_name": config.model_name,
            "litellm_params": {
                "model": config.model_name,  # 重要: 'model'キーを明示的に設定
                **config.litellm_params,
            },
        }

        if config.alias:
            model_entry["alias"] = config.alias

        if config.timeout:
            model_entry["timeout"] = config.timeout

        if config.weight:
            model_entry["weight"] = config.weight

        self.router.add_model(model_entry)
        self.configs.append(config)
        logger.info(f"Added model {config.model_name} to router")

    def get_router(self) -> Optional[Router]:
        """
        ルーターを取得する

        Returns:
            ルーターインスタンスまたはNone
        """
        return self.router if self.enabled else None

    def is_enabled(self) -> bool:
        """
        ルーターが有効かどうかを返す

        Returns:
            ルーターが有効な場合はTrue、そうでない場合はFalse
        """
        return self.enabled

def get_router() -> RouterManager:
    """
    RouterManagerのシングルトンインスタンスを取得する

    Returns:
        RouterManagerインスタンス
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = RouterManager()
    return _router_instance

def init_router_from_db():
    """
    データベースからモデル情報を取得してルーターを初期化する

    Note:
        この関数はアプリケーション起動時に呼び出されることを想定しています。
        DB内の有効なモデルをすべて取得し、ルーターに登録します。
    """
    # 循環importを避けるためにここでimport
    from app.utils.db.models import get_model_repository

    try:
        # DBからアクティブなモデルを取得
        model_repo = get_model_repository()
        active_models = model_repo.get_all_models()

        # アクティブなモデルだけをフィルタリング
        active_models = [m for m in active_models if m["is_active"]]

        if not active_models:
            logger.warning("No active models found in database. Router initialization skipped.")
            return

        # モデル設定を作成
        configs = []
        for db_model in active_models:
            provider_name = db_model["provider_name"]
            model_name = db_model["name"]

            # モデルのフルネーム
            full_model_name = format_litellm_model_name(provider_name, model_name)

            # パラメータを設定
            litellm_params = {}

            # APIキーとエンドポイントの設定
            if db_model.get("api_key"):
                litellm_params["api_key"] = db_model["api_key"]

            if db_model.get("endpoint"):
                litellm_params["base_url"] = db_model["endpoint"]

            # プロバイダー固有のオプションを追加
            provider_options = get_provider_options(provider_name)
            if provider_options:
                for key, value in provider_options.items():
                    # 既存の値は上書きしない
                    if key not in litellm_params:
                        litellm_params[key] = value

            # モデルパラメータがある場合は追加
            if db_model.get("parameters"):
                model_params = db_model["parameters"]
                # デフォルトでモデルパラメータがLiteLLMパラメータを上書き
                litellm_params.update(model_params)

            # モデル設定を作成
            config = ModelConfig(
                model_name=full_model_name,
                litellm_params=litellm_params,
                alias=db_model.get("display_name", model_name),
                timeout=settings.MODEL_TIMEOUT,
                weight=1  # デフォルトウェイト
            )

            configs.append(config)

        # ルーターを初期化
        router_manager = get_router()
        router_manager.initialize(configs, routing_strategy=settings.ROUTING_STRATEGY)

        logger.info(f"Router initialized with {len(configs)} models from database")
    except Exception as e:
        logger.error(f"Error initializing router from database: {e}", exc_info=True)

def update_router_model(db_model: Dict[str, Any]) -> bool:
    """
    ルーターのモデル設定を更新する

    Args:
        db_model: データベースから取得したモデル情報

    Returns:
        更新成功の場合はTrue、それ以外はFalse
    """
    try:
        router_manager = get_router()
        if not router_manager.is_enabled():
            # ルーターが初期化されていない場合は初期化から
            init_router_from_db()
            return True

        provider_name = db_model["provider_name"]
        model_name = db_model["name"]

        # モデルのフルネーム
        full_model_name = format_litellm_model_name(provider_name, model_name)

        # パラメータを設定
        litellm_params = {
            "model": full_model_name
        }

        # APIキーとエンドポイントの設定
        if db_model.get("api_key"):
            litellm_params["api_key"] = db_model["api_key"]

        if db_model.get("endpoint"):
            litellm_params["base_url"] = db_model["endpoint"]

        # プロバイダー固有のオプションを追加
        provider_options = get_provider_options(provider_name)
        if provider_options:
            for key, value in provider_options.items():
                # 既存の値は上書きしない
                if key not in litellm_params:
                    litellm_params[key] = value

        # モデルパラメータがある場合は追加
        if db_model.get("parameters"):
            model_params = db_model["parameters"]
            # デフォルトでモデルパラメータがLiteLLMパラメータを上書き
            litellm_params.update(model_params)

        # モデル設定を作成
        config = ModelConfig(
            model_name=full_model_name,
            litellm_params=litellm_params,
            alias=db_model.get("display_name", model_name),
            timeout=settings.MODEL_TIMEOUT,
            weight=1  # デフォルトウェイト
        )

        # ルーターを更新（既存のモデルは追加時に更新される）
        router_manager.add_model(config)

        return True
    except Exception as e:
        logger.error(f"Error updating router model: {e}", exc_info=True)
        return False
