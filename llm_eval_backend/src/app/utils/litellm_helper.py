"""
LiteLLM関連のユーティリティ関数とヘルパークラス
"""
import logging
import json
import os
import hashlib
import re
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
import litellm
from litellm import Router, acompletion
from pydantic import BaseModel
from app.config import get_settings

# 設定の取得
settings = get_settings()
logger = logging.getLogger(__name__)

# APIキー環境変数の無効化
# 環境変数からのLLM APIキー読み込みを防止するため、統一されたプレースホルダー値を設定
# このAPIキー形式は実際のOpenAIキーではなくLiteLLMにヒントを与えるための特殊なフォーマット
DISABLED_API_KEY = "sk-INVALID-API-KEY-CHECK-PROVIDER-SETTINGS"
# 環境変数用のプレースホルダー
PLACEHOLDER_API_KEY = "sk-disabled-environment-variable"
logger.info("環境変数からのAPIキー読み込みを無効化します")

# 主要なLLMプロバイダの環境変数をオーバーライド
ENV_VARS_TO_BLOCK = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "REPLICATE_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "MISTRAL_API_KEY",
    "HUGGINGFACE_API_KEY",
    "GROQ_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "TOGETHERAI_API_KEY",
    "PALM_API_KEY",
    "GEMINI_API_KEY",
    "AI21_API_KEY",
    "ANYSCALE_API_KEY",
    "CLAUDE_API_KEY"
]

# 環境変数アクセスをモニタリングする関数
def log_env_var_access(var_name):
    """環境変数へのアクセスを記録する関数"""
    # スタックトレースを取得して呼び出し元を特定
    import traceback
    stack = traceback.extract_stack()
    # 自分自身と os.environ 以外の最初の呼び出し元を取得
    caller = None
    for frame in reversed(stack[:-1]):  # 最後のフレーム（この関数自体）を除外
        if 'os.py' not in frame.filename and 'litellm_helper.py' not in frame.filename:
            caller = f"{frame.filename}:{frame.lineno}"
            break
    
    logger.warning(f"⚠️ 環境変数 {var_name} へのアクセスが検出されました: 呼び出し元: {caller or '不明'}")
    return PLACEHOLDER_API_KEY

# 環境変数辞書をモンキーパッチ
original_getitem = os.environ.__class__.__getitem__
def monitored_getitem(self, key):
    if key in ENV_VARS_TO_BLOCK:
        return log_env_var_access(key)
    return original_getitem(self, key)
os.environ.__class__.__getitem__ = monitored_getitem

# すべての環境変数をオーバーライド
for var_name in ENV_VARS_TO_BLOCK:
    os.environ[var_name] = PLACEHOLDER_API_KEY
    logger.debug(f"環境変数を無効化: {var_name}")

# LiteLLMの環境変数からのAPIキー読み込みを無効化
litellm.use_client = False  # APIキーの自動検出を無効化

# LiteLLMの元のcompletion関数とacompletion関数を保存
original_completion = litellm.completion
original_acompletion = litellm.acompletion

# プロバイダ/モデル形式から情報を抽出する関数
def parse_model_name(model_name: str) -> Tuple[str, str]:
    """
    LiteLLM形式のモデル名からプロバイダとモデル名を抽出する
    
    Args:
        model_name: provider/model形式のモデル名
        
    Returns:
        (provider, model)のタプル
    """
    if "/" in model_name:
        parts = model_name.split("/", 1)
        return parts[0].lower(), parts[1]
    else:
        # フォールバック: プロバイダがない場合は推測する
        if model_name.startswith(("gpt-", "text-davinci-")):
            return "openai", model_name
        elif model_name.startswith("claude-"):
            return "anthropic", model_name
        else:
            # デフォルトはそのまま返す
            return "", model_name

# カスタム例外コールバックを設定（LiteLLMのエラーをカスタマイズ）
def custom_exception_handler(exception, **kwargs):
    model = kwargs.get("model", "unknown")
    provider_name = "unknown"
    
    # プロバイダ名を推測
    if model:
        if "/" in model:
            provider_name = model.split("/")[0]
        elif model.startswith("gpt-") or model.startswith("text-davinci-"):
            provider_name = "openai"
        elif model.startswith("claude-"):
            provider_name = "anthropic"
        elif model.startswith("mistral-") or model.startswith("mixtral-"):
            provider_name = "mistral"
        elif model.startswith("gemini-"):
            provider_name = "google"
    
    # 無効なAPIキーを検出（当システム独自の無効APIキーパターン）
    if "api_key" in kwargs and kwargs["api_key"] and "sk-invalid-not-set" in kwargs["api_key"]:
        custom_error = f"APIキーが設定されていません: プロバイダ {provider_name} のモデル {model} の設定を確認してください。管理画面でプロバイダまたはモデル設定にAPIキーを追加してください。"
        logger.error(f"APIキー未設定エラー: {custom_error}")
        from litellm.exceptions import AuthenticationError
        raise AuthenticationError(custom_error)
    
    # APIキーエラーを検出して、より明確なメッセージに変更
    if "AuthenticationError" in str(exception) or "Incorrect API key provided" in str(exception) or "sk-" in str(exception):
        # 元のエラーメッセージを保存
        original_error = str(exception)
        # 独自のエラーメッセージを作成
        new_error_message = (
            f"APIキーが正しく設定されていないか不足しています。プロバイダ: {provider_name}, モデル: {model}\n"
            f"管理画面でプロバイダの設定を確認し、有効なAPIキーを設定してください。\n"
        )
        logger.error(f"認証エラー検出: {new_error_message}")
        
        # 例外を置き換える
        from litellm.exceptions import AuthenticationError
        raise AuthenticationError(new_error_message)
    
    # URLエラーの検出（すべてのプロバイダ共通）
    if "Invalid URL" in str(exception) or "404 Not Found" in str(exception):
        from litellm.exceptions import BadRequestError
        
        # base_urlを確認
        base_url = kwargs.get("base_url", "")
        error_message = str(exception)
        
        # 修正方法を提案
        fix_suggestion = (
            f"エンドポイントURLエラー検出: ({error_message})\n"
            f"プロバイダ: {provider_name}, モデル: {model}\n"
            f"現在のbase_url: {base_url}\n"
            f"修正方法: プロバイダ設定で正しいエンドポイントを設定してください。\n"
            f"- OpenAIの場合: 'https://api.openai.com/v1'\n"
            f"- Anthropicの場合: 'https://api.anthropic.com'\n"
            f"- Ollamaの場合: 'http://localhost:11434' または実際のOllamaサーバーアドレス\n"
        )
        logger.error(fix_suggestion)
        
        # 例外を置き換える
        raise BadRequestError(fix_suggestion)
    
    # その他のエラーはそのまま
    return exception
    
# LiteLLMのcompletion関数で使われるヘルパー関数
def ensure_api_key(kwargs):
    """APIキーが常に指定されるようにする共通ヘルパー関数"""
    # APIキーがない場合は、明示的なエラーメッセージを設定
    if "api_key" not in kwargs or not kwargs["api_key"]:
        model = kwargs.get("model", "unknown")
        provider_name = "unknown"
        
        # プロバイダ名を推測
        if model:
            if "/" in model:
                provider_name = model.split("/")[0]
            elif model.startswith("gpt-") or model.startswith("text-davinci-"):
                provider_name = "openai"
            elif model.startswith("claude-"):
                provider_name = "anthropic"
            elif model.startswith("mistral-") or model.startswith("mixtral-"):
                provider_name = "mistral"
            elif model.startswith("gemini-"):
                provider_name = "google"
        
        # 明示的に無効なAPIキーを設定（APIキーエラーを発生させる）
        error_message = f"APIキーが設定されていません: プロバイダ {provider_name} のモデル {model} の設定を確認してください。管理画面でAPIキーを設定してください。"
        logger.error(error_message)
        kwargs["api_key"] = "sk-invalid-not-set-please-configure-in-admin"
        
        logger.warning(f"APIキーが明示的に指定されていません: {error_message}")
    
    return kwargs

# completionとacompletionを上書きして、APIキーが常に指定されるようにする
def enforced_completion(*args, **kwargs):
    """API KeyパラメータをLiteLLMのcompletionに必須化するラッパー関数"""
    kwargs = ensure_api_key(kwargs)
    # 元の関数を呼び出す
    return original_completion(*args, **kwargs)

async def enforced_acompletion(*args, **kwargs):
    """API KeyパラメータをLiteLLMのacompletionに必須化する非同期ラッパー関数"""
    kwargs = ensure_api_key(kwargs)
    # 元の関数を呼び出す
    return await original_acompletion(*args, **kwargs)

# LiteLLMのcompletionとacompletionをオーバーライド
litellm.completion = enforced_completion
litellm.acompletion = enforced_acompletion

# LiteLLMの新しいバージョンで register_exception_handler が利用可能か確認
has_exception_handler = hasattr(litellm, 'register_exception_handler')
if has_exception_handler:
    # 例外ハンドラを登録 (新しいバージョンの場合)
    try:
        litellm.register_exception_handler(custom_exception_handler)
        logger.info("LiteLLMの例外ハンドラを登録しました")
    except Exception as e:
        logger.warning(f"LiteLLMの例外ハンドラ登録に失敗しました: {e}")
else:
    logger.warning("LiteLLMのバージョンが古いため、例外ハンドラの登録をスキップします")

# 各プロバイダのデフォルトエンドポイント
# 注意: デフォルトエンドポイントは使用せず、プロバイダ登録時に正しいエンドポイントを設定する

# LiteLLMの内部デフォルト値をオーバーライド
# APIキーが見つからない場合の内部的なフォールバック値を置き換える
PROVIDER_KEYS = [
    "openai_key", "anthropic_key", "cohere_key", "replicate_key", 
    "google_palm_key", "mistral_key", "huggingface_key", "groq_key", 
    "azure_key", "together_key"
]

# すべてのプロバイダキーを一括で設定
for key_name in PROVIDER_KEYS:
    setattr(litellm, key_name, DISABLED_API_KEY)

# LiteLLMのモデル検証時の環境変数自動読み込みを無効化
# 古いバージョンのLiteLLMではmodel_cost_map_validationが存在しない場合がある
has_model_validation = hasattr(litellm, 'model_cost_map_validation')
if has_model_validation:
    try:
        # モンキーパッチでmodel_cost_map_validationの関数を書き換え
        original_model_validation = litellm.model_cost_map_validation
        def disabled_model_validation(*args, **kwargs):
            # 環境変数からAPIキーを読み込まないようにする
            kwargs["api_key"] = DISABLED_API_KEY
            # 検証をスキップするためにデフォルト値を返す
            return {
                "input_cost_per_token": 0.0,
                "output_cost_per_token": 0.0,
                "token_limit": 4096
            }
        litellm.model_cost_map_validation = disabled_model_validation
        logger.info("LiteLLMのモデル検証関数をオーバーライドしました")
    except Exception as e:
        logger.warning(f"LiteLLMのモデル検証関数のオーバーライドに失敗しました: {e}")
else:
    logger.warning("LiteLLMのバージョンが古いため、モデル検証関数のオーバーライドをスキップします")

# モンキーパッチでlitellmの環境変数検索関数を無効化
original_get_secret = litellm.utils.get_secret
def disabled_get_secret(secret_name, default=None):
    logger.warning(f"環境変数からのシークレット取得が試行されました: {secret_name}")
    return DISABLED_API_KEY
litellm.utils.get_secret = disabled_get_secret

logger.info("LiteLLMの環境変数からのAPIキー読み込みを無効化しました")

# モデル情報のグローバルキャッシュ
MODEL_INFO_CACHE = {}

# ルーターインスタンス（シングルトン）
_router_instance = None

def init_litellm_cache():
    """
    LiteLLMのキャッシュを初期化する関数

    キャッシュが有効な場合はLiteLLMのキャッシュを有効化します
    """
    # 環境変数によるAPIキー設定を再度無効化（安全のため）
    for var_name in ENV_VARS_TO_BLOCK:
        if os.environ.get(var_name) != PLACEHOLDER_API_KEY:
            os.environ[var_name] = PLACEHOLDER_API_KEY
            logger.warning(f"環境変数 {var_name} が変更されたため再設定しました")
    
    # LiteLLMの環境変数依存を無効化（再設定）
    litellm.use_client = False
    
    # LiteLLMの内部デフォルト値をオーバーライド（再設定）
    for key_name in PROVIDER_KEYS:
        setattr(litellm, key_name, DISABLED_API_KEY)
    
    # 各種モンキーパッチと設定の再適用
    litellm.utils.get_secret = disabled_get_secret
    # 例外ハンドラ登録（バージョンを確認）
    if has_exception_handler:
        try:
            litellm.register_exception_handler(custom_exception_handler)
        except Exception:
            pass
    # モデル検証関数のオーバーライド（もし存在する場合）
    if has_model_validation:
        try:
            litellm.model_cost_map_validation = disabled_model_validation
        except Exception:
            pass
    litellm.completion = enforced_completion
    litellm.acompletion = enforced_acompletion
    
    # キャッシュ設定
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
            },
            # Ollamaは通常APIキーは不要だが、エンドポイント設定が必要
            "stream": False  # ストリーミングを無効化
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
    Ollamaの場合のみ「provider/model」の形式を使用し、
    その他のプロバイダは「model」の形式を使用します。

    Args:
        provider_name: プロバイダ名
        model_name: モデル名

    Returns:
        LiteLLM形式のモデル名
    """
    # プロバイダ名を小文字に変換（LiteLLMの要件）
    provider_name_lower = provider_name.lower()
    
    # 既にprovider/model形式の場合はモデル名のみを抽出
    if "/" in model_name:
        # すでにprovider/model形式の場合は、Ollamaの場合はそのまま返し、
        # それ以外はモデル名部分だけを抽出して返す
        parts = model_name.split("/", 1)
        if provider_name_lower == "ollama":
            return model_name
        else:
            return parts[1]  # model部分のみ返す
    
    # Ollamaの場合のみprovider/model形式で返す
    if provider_name_lower == "ollama":
        return f"{provider_name_lower}/{model_name}"
    else:
        # それ以外のプロバイダはモデル名のみを返す
        return model_name

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
            routing_strategy_args={},
            # 環境変数からのAPIキー読み込みを無効化
            default_litellm_params={},  # デフォルトパラメータは空にして、各モデルのパラメータを優先
            set_verbose=False  # 詳細なログを無効化（APIキー情報が含まれる可能性があるため）
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

        # LiteLLM バージョン互換対応（1.68.0）
        # add_model メソッドがない場合は新しいルーターを作成する
        try:
            # 新しいバージョンのLiteLLMの場合
            if hasattr(self.router, 'add_model'):
                # モデルを追加（モデルごとのパラメータを使用）
                self.router.add_model(
                    model_entry,
                    default_litellm_params={}  # デフォルトパラメータは空にして、各モデルのパラメータを優先
                )
            else:
                # 古いバージョンのLiteLLMの場合は、新しいルーターを作成
                logger.info(f"Router does not have add_model method. Creating new router with updated model list.")
                
                # 既存のモデルリストに新しいモデルを追加
                updated_model_list = self.router.model_list + [model_entry]
                
                # 新しいルーターを作成して置き換え
                self.router = Router(
                    model_list=updated_model_list,
                    routing_strategy=self.router.routing_strategy,
                    fallbacks=self.router.fallbacks if hasattr(self.router, 'fallbacks') else [],
                    context_window_fallbacks=self.router.context_window_fallbacks if hasattr(self.router, 'context_window_fallbacks') else [],
                    num_retries=settings.MODEL_RETRIES,
                    timeout=settings.MODEL_TIMEOUT,
                    default_litellm_params={},
                    set_verbose=False
                )
            
            # 設定を追加
            self.configs.append(config)
            logger.info(f"Added model {config.model_name} to router")
            
        except Exception as e:
            logger.error(f"Error adding model to router: {e}", exc_info=True)
            # エラーが発生しても続行できるように例外をキャッチ

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

def has_api_key(provider_name: str = None, model_name: str = None, provider_id: int = None) -> bool:
    """
    プロバイダまたはモデルがAPIキーを持っているかどうかを確認する

    Args:
        provider_name: プロバイダ名
        model_name: モデル名
        provider_id: プロバイダID

    Returns:
        APIキーが設定されている場合はTrue、そうでない場合はFalse
    """
    # 循環importを避けるためにここでimport
    from app.utils.db.models import get_model_repository
    from app.utils.db.providers import get_provider_repository

    try:
        # プロバイダの確認
        if provider_id is not None:
            provider_repo = get_provider_repository()
            provider = provider_repo.get_provider_by_id(provider_id)
            if provider and provider.get("api_key"):
                return True
        
        # プロバイダ名での確認
        if provider_name:
            provider_repo = get_provider_repository()
            providers = provider_repo.get_all_providers()
            for provider in providers:
                if provider.get("name") == provider_name and provider.get("api_key"):
                    return True
        
        # モデル名での確認
        if model_name:
            model_repo = get_model_repository()
            models = model_repo.get_all_models()
            for model in models:
                if model.get("name") == model_name and model.get("api_key"):
                    return True
                
                # モデルにAPIキーがなくても関連プロバイダにあるかチェック
                if model.get("name") == model_name and model.get("provider_id"):
                    provider_repo = get_provider_repository()
                    provider = provider_repo.get_provider_by_id(model["provider_id"])
                    if provider and provider.get("api_key"):
                        return True
                    
        return False
    
    except Exception as e:
        logger.error(f"APIキー確認エラー: {e}")
        return False

def validate_api_key(api_key: str, provider_name: str = None) -> bool:
    """
    APIキーが有効かどうかを検証する

    Args:
        api_key: 検証するAPIキー
        provider_name: プロバイダ名（オプション）

    Returns:
        有効な場合はTrue、無効な場合はFalse
    """
    # None、空文字は無効
    if not api_key:
        return False
        
    # デモキー形式は無効
    if api_key.startswith(("sk-your", "DEMO", "TEST", "INVALID", "dummy", "placeholder")):
        return False
    
    # Ollamaの場合は特別処理（APIキーが不要）
    if provider_name and provider_name.lower() == "ollama":
        # Ollamaは任意の文字列をAPIキーとして受け付ける（実際には使用されない）
        # "ollama"という文字列がAPIキーとして設定されている場合は有効と見なす
        if api_key == "ollama" or api_key.startswith("ollama_"):
            return True
        else:
            # Ollamaではないキーが設定されていればそれも有効（ただしエンドポイントも必要）
            return len(api_key) >= 5
    
    # プロバイダごとの検証
    if provider_name:
        if provider_name.lower() == "openai" and not api_key.startswith(("sk-", "AZURE_")):
            # OpenAIのAPIキーは通常sk-で始まる
            return len(api_key) >= 20  # より長いキーは有効と仮定
        elif provider_name.lower() == "anthropic" and not api_key.startswith("sk-ant-"):
            # Anthropicのキーはsk-ant-で始まるが、より長いキーであれば有効と仮定
            return len(api_key) >= 20
    
    # 一般的なAPIキーのパターンをチェック（最低限の長さと形式）
    if len(api_key) < 10:  # APIキーは通常もっと長い
        return False
    
    # 有効なAPIキーと判断
    return True

def get_api_key_error_message(provider_name: str, model_name: str) -> str:
    """
    APIキーが設定されていない場合のエラーメッセージを生成する

    Args:
        provider_name: プロバイダ名
        model_name: モデル名

    Returns:
        エラーメッセージ
    """
    # プロバイダごとの設定方法や注意点を含める
    provider_specific_info = ""
    if provider_name.lower() == "openai":
        provider_specific_info = "OpenAIのAPIキーはsk-で始まる文字列です。"
    elif provider_name.lower() == "anthropic":
        provider_specific_info = "AnthropicのAPIキーはsk-ant-で始まる文字列です。"
    elif provider_name.lower() == "ollama":
        provider_specific_info = "Ollamaはローカルモデルのため通常APIキーは不要ですが、エンドポイントの設定が必要です。"
    
    return (
        f"APIキーが設定されていません: モデル '{model_name}' またはプロバイダ '{provider_name}' の設定を確認してください。\n"
        f"管理画面でプロバイダまたはモデル設定にAPIキーを追加してください。{provider_specific_info}\n"
        f"注意: 環境変数からのAPIキー読み込みは無効化されています。すべてのAPIキーはデータベースに保存する必要があります。"
    )

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

            # モデル名のフォーマット
            full_model_name = format_litellm_model_name(provider_name, model_name)

            # パラメータを設定 - モデル名も含める
            litellm_params = {
                "model": full_model_name
            }
            
            # OpenAIの場合はエンドポイントを指定しない（デフォルトを使用）
            # これによりURL構築の問題を回避
            if provider_name.lower() == "openai":
                logger.info(f"OpenAIの場合、エンドポイントは指定せずデフォルトを使用")

            # プロバイダ情報を取得（APIキーを確認するため）
            provider = None
            try:
                # プロバイダ情報を取得
                from app.utils.db.providers import get_provider_repository
                provider_repo = get_provider_repository()
                provider = provider_repo.get_provider_by_id(db_model["provider_id"])
                if provider:
                    logger.info(f"Provider found: {provider['name']} (ID: {provider['id']})")
                else:
                    logger.warning(f"Provider not found for ID: {db_model['provider_id']}")
            except Exception as e:
                logger.error(f"Error fetching provider: {e}")

            # APIキーとエンドポイントの設定
            # 優先順位: 1. モデルのAPI Key, 2. プロバイダのAPI Key, 3. 明示的なエラーメッセージ (環境変数を利用しない)
            api_key = None
            api_key_source = None
            
            if db_model.get("api_key"):
                api_key = db_model["api_key"]
                api_key_source = f"モデル設定: {model_name}"
                logger.info(f"Using API key from model configuration: {model_name}")
            elif provider and provider.get("api_key"):
                api_key = provider["api_key"]
                api_key_source = f"プロバイダ設定: {provider['name']}"
                logger.info(f"Using API key from provider: {provider['name']}")
            else:
                api_key = None
            
            if api_key:
                # APIキーを検証（プロバイダ名も渡す）
                if validate_api_key(api_key, provider_name):
                    # 有効なAPIキーの場合
                    litellm_params["api_key"] = api_key
                    
                    # APIキーの末尾数桁を記録（デバッグ用）
                    if len(api_key) > 7:
                        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
                        logger.info(f"API key loaded from {api_key_source}: {masked_key}")
                else:
                    # 無効なAPIキーの場合
                    logger.error(f"検出されたAPIキーは無効です: {api_key if len(api_key) < 8 else api_key[:4] + '...'}")
                    logger.warning(f"無効なAPIキーです。プロバイダ設定またはモデル設定で有効なAPIキーを設定してください")
                    # APIキーが未設定の場合と同じ扱いにする
                    api_key = None
            
            # APIキーが見つからない場合
            if not api_key:
                # 詳細なエラーメッセージを表示
                error_message = get_api_key_error_message(provider_name, model_name)
                logger.warning(f"APIキー未設定エラー: {error_message}")
                
                # APIキーを設定しない - この場合、LiteLLMのリクエスト時にエラーが発生する
                # Router は各モデルのパラメータを使用し、デフォルトのAPIキーは使用しない

            # エンドポイントの設定（モデルにないならプロバイダから）
            endpoint = None
            if db_model.get("endpoint"):
                endpoint = db_model["endpoint"]
            elif provider and provider.get("endpoint"):
                endpoint = provider["endpoint"]
                
            if endpoint:
                litellm_params["base_url"] = endpoint

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

        # モデル名のフォーマット
        full_model_name = format_litellm_model_name(provider_name, model_name)

        # パラメータを設定
        litellm_params = {
            "model": full_model_name
        }

        # プロバイダ情報を取得（APIキーを確認するため）
        provider = None
        try:
            # プロバイダ情報を取得
            from app.utils.db.providers import get_provider_repository
            provider_repo = get_provider_repository()
            provider = provider_repo.get_provider_by_id(db_model["provider_id"])
        except Exception as e:
            logger.error(f"Error fetching provider: {e}")

        # APIキーの設定（優先順位: モデル > プロバイダ > 明示的なエラーメッセージ）
        api_key = None
        api_key_source = None
        
        if db_model.get("api_key"):
            api_key = db_model["api_key"]
            api_key_source = f"モデル設定: {model_name}"
            logger.info(f"Using API key from model configuration: {model_name}")
        elif provider and provider.get("api_key"):
            api_key = provider["api_key"]
            api_key_source = f"プロバイダ設定: {provider['name']}"
            logger.info(f"Using API key from provider: {provider['name'] if provider else 'unknown'}")
            
        if api_key:
            # APIキーを検証（プロバイダ名も渡す）
            if validate_api_key(api_key, provider_name):
                # 有効なAPIキーの場合
                litellm_params["api_key"] = api_key
                
                # APIキーの末尾数桁を記録（デバッグ用）
                if len(api_key) > 7:
                    masked_key = f"{api_key[:4]}...{api_key[-4:]}"
                    logger.info(f"API key loaded from {api_key_source}: {masked_key}")
            else:
                # 無効なAPIキーの場合
                logger.error(f"検出されたAPIキーは無効です: {api_key if len(api_key) < 8 else api_key[:4] + '...'}")
                logger.warning(f"無効なAPIキーです。プロバイダ設定またはモデル設定で有効なAPIキーを設定してください")
                # APIキーが未設定の場合と同じ扱いにする
                api_key = None
        
        # APIキーが見つからない場合や無効な場合
        if not api_key:
            # 詳細なエラーメッセージを表示
            error_message = get_api_key_error_message(provider_name, model_name)
            logger.warning(f"APIキー未設定エラー: {error_message}")
            
            # APIキーを設定しない - この場合、LiteLLMのリクエスト時にエラーが発生する
            # Router は各モデルのパラメータを使用し、デフォルトのAPIキーは使用しない

        # プロバイダ名は直接設定せず、モデル名に含める形式を使用
        # provider パラメータは LiteLLM API では受け付けられないため削除
        
        # エンドポイント取得
        endpoint = None
        if db_model.get("endpoint"):
            endpoint = db_model["endpoint"]
        elif provider and provider.get("endpoint"):
            endpoint = provider["endpoint"]
        
        # エンドポイント設定（Ollamaは必須、その他は明示的に指定がある場合のみ）
        if provider_name.lower() == "ollama":
            # Ollamaの場合はエンドポイント必須
            if endpoint and endpoint.strip():
                # プロトコル追加（必要な場合）
                if not endpoint.startswith(("http://", "https://")):
                    endpoint = "http://" + endpoint
                
                litellm_params["base_url"] = endpoint
                logger.info(f"Ollamaのエンドポイント設定: {endpoint}")
            else:
                logger.warning(f"Ollamaはエンドポイント指定が必須です")
        elif endpoint and endpoint.strip():
            # その他のプロバイダは明示的に指定がある場合のみ設定
            # プロトコル追加（必要な場合）
            if not endpoint.startswith(("http://", "https://")):
                endpoint = "https://" + endpoint
                
            litellm_params["base_url"] = endpoint
            logger.info(f"{provider_name}のエンドポイント設定: {endpoint}")
        else:
            # エンドポイント設定なし - LiteLLMのデフォルト動作に任せる
            logger.info(f"{provider_name}はエンドポイント設定を行わず、LiteLLMのデフォルト動作を使用")

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

        # LiteLLM 1.68.0 互換性対応
        try:
            # ルーターを更新
            router_manager.add_model(config)
            logger.info(f"Successfully updated router with model: {model_name}")
            return True
        except AttributeError as ae:
            logger.warning(f"Attribute error when adding model to router: {ae}")
            # ルーターを初期化しなおす方法で対応
            try:
                # 既存の設定に新しい設定を追加
                new_configs = router_manager.configs + [config]
                # ルーターを再初期化
                router_manager.initialize(new_configs, routing_strategy=settings.ROUTING_STRATEGY)
                logger.info(f"Router reinitialized successfully with updated model list")
                return True
            except Exception as re_init_error:
                logger.error(f"Failed to reinitialize router: {re_init_error}", exc_info=True)
                return False
        except Exception as e:
            logger.error(f"Unknown error when updating router model: {e}", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Error updating router model: {e}", exc_info=True)
        return False
