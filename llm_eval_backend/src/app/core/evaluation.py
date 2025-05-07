from typing import List, Dict, Any, Optional, Union
import asyncio
from pathlib import Path
import json
import litellm
from litellm import acompletion, Router
import os
import logging
import pandas as pd
from tqdm import tqdm
import sys
import datetime
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 設定のインポート
from app.config import get_settings

# 評価メトリクスのインポート（動的読み込みを使用）
from app.metrics import get_metrics_functions

# LiteLLMヘルパー関数のインポート
from app.utils.litellm_helper import (
    format_litellm_model_name,
    get_provider_options,
    get_router,
    init_router_from_db,
    parse_model_name
)

# 設定の取得
settings = get_settings()

# 結果ディレクトリの作成
settings.initialize_dirs()

# ロギングの設定
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)


# 評価メトリクスの関数マッピングは実行時に取得するためグローバルでは定義しない
# (get_metrics_functions は parameters を引数に取るようになったため)

# LiteLLM呼び出しの例外定義
class LiteLLMAPIError(Exception):
    """LiteLLM API呼び出し中のエラー"""
    pass

class LiteLLMTimeoutError(Exception):
    """LiteLLM API呼び出しのタイムアウトエラー"""
    pass

class LiteLLMRateLimitError(Exception):
    """LiteLLM APIのレート制限エラー"""
    pass

class ModelNotAvailableError(Exception):
    """モデルが利用できないエラー"""
    pass

async def get_few_shot_samples(dataset_name: str, n_shots: int) -> List[Dict[str, str]]:
    """
    Few-shotサンプルを取得する関数

    Args:
        dataset_name: データセット名
        n_shots: サンプル数

    Returns:
        Few-shotサンプルのリスト
    """
    if n_shots == 0:
        return []

    # データセット名からパスを合成（run_evaluationと同様の処理）
    if '/' in dataset_name:
        # パスが含まれている場合はそのまま使用
        if dataset_name.endswith('.json'):
            # 完全なパスとして扱う
            dataset_path = Path(dataset_name)
        else:
            # パスが含まれているが拡張子がない場合
            dataset_path = Path(f"{dataset_name}.json")
        base_name = dataset_name.split('/')[-1]
        if base_name.endswith('.json'):
            base_name = base_name[:-5]  # .jsonを削除
    else:
        # データセット名のみの場合
        base_name = dataset_name
        # 絶対パスで生成
        dataset_path = settings.NSHOT_DATASETS_DIR / f"{base_name}.json"
    
    logger.info(f"Looking for few-shot data at: {dataset_path}")

    with dataset_path.open(encoding="utf-8") as f:
        train_data = json.load(f)

    few_shots = []
    for i in range(min(n_shots, len(train_data["samples"]))):
        sample = train_data["samples"][i]
        few_shots.append({"role": "user", "content": sample["input"]})
        few_shots.append({"role": "assistant", "content": sample["output"]})

    return few_shots

async def format_prompt(instruction: str, input_text: str, few_shots: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    プロンプトをフォーマットする関数

    Args:
        instruction: タスクの指示
        input_text: 入力テキスト
        few_shots: Few-shotサンプル

    Returns:
        メッセージのリスト
    """
    messages = []

    # システムメッセージの作成
    is_english = "mmlu_en" in instruction
    if is_english:
        message_intro = "The following text provides instructions for a certain task."
    else:
        message_intro = "以下に、あるタスクを説明する指示があり、それに付随する入力が更なる文脈を提供しています。リクエストを適切に完了するための回答を記述してください。"

    system_message = f"{message_intro}\n\n{instruction}"
    messages.append({"role": "system", "content": system_message})

    # Few-shotサンプルの追加
    if few_shots:
        messages.extend(few_shots)

    # ユーザー入力の追加
    messages.append({"role": "user", "content": input_text})

    return messages

# リトライポリシーを使用したモデル呼び出し関数
@retry(
    retry=retry_if_exception_type((LiteLLMTimeoutError, LiteLLMRateLimitError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def call_model_with_retry(
    messages: List[Dict[str, str]],
    model_name: str,
    provider_name: str,
    max_tokens: int,
    temperature: float,
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    リトライロジックを含むモデル呼び出し関数

    Args:
        messages: メッセージのリスト
        model_name: モデル名
        provider_name: プロバイダ名
        max_tokens: 最大トークン数
        temperature: 温度
        additional_params: 追加パラメータ

    Returns:
        LiteLLMのレスポンス
    """

    # プロバイダとモデル名を結合（LiteLLMの形式に合わせる）
    full_model_name = format_litellm_model_name(provider_name, model_name)

    # リクエストパラメータの設定
    request_params = {
        "model": full_model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # 追加パラメータの適用
    if additional_params:
        request_params.update(additional_params)

    # プロバイダー固有のオプションを取得
    provider_options = get_provider_options(provider_name)
    if provider_options:
        # ヘッダー情報を更新
        if "headers" in provider_options:
            request_params["headers"] = provider_options.get("headers", {})

        # API Key設定
        if "api_key" in provider_options:
            request_params["api_key"] = provider_options["api_key"]

        # ベースURLの設定
        if "base_url" in provider_options:
            request_params["base_url"] = provider_options["base_url"]

    try:
        # デバッグ用：リクエストパラメータをログに記録
        safe_params = request_params.copy()
        if "api_key" in safe_params:
            api_key = safe_params["api_key"]
            # APIキーの実際の値をログに記録（これは一時的なデバッグ用、後で削除する）
            logger.error(f"EVALUATION USING API KEY: {api_key} (type: {type(api_key)})")
            if api_key.startswith("sk-your"):
                logger.error(f"EVAL: デモキー検出! APIキーはデモキー（'sk-your'で始まる）です: {api_key}")
            # マスクしたキーをログに記録
            if len(api_key) > 7:
                safe_params["api_key"] = f"{api_key[:4]}...{api_key[-4:]}"
            
        logger.info(f"Calling model with params: {safe_params}")
        
        # カスタムタイムアウト設定でAPIを呼び出し
        response = await asyncio.wait_for(
            acompletion(**request_params),
            timeout=settings.MODEL_TIMEOUT
        )
        return response
    except asyncio.TimeoutError:
        logger.warning(f"Timeout calling model {full_model_name}")
        raise LiteLLMTimeoutError(f"Timeout calling model {full_model_name}")
    except Exception as e:
        error_message = str(e).lower()
        if "rate limit" in error_message or "too many requests" in error_message:
            logger.warning(f"Rate limit error calling model {full_model_name}: {e}")
            # レート制限エラーは再試行
            raise LiteLLMRateLimitError(f"Rate limit error: {str(e)}")
        else:
            # その他のエラーは記録して再発生
            logger.error(f"Error calling model {full_model_name}: {e}")
            raise LiteLLMAPIError(f"API error: {str(e)}")

async def try_fallback_providers(
    messages: List[Dict[str, str]],
    primary_provider: str,
    primary_model: str,
    max_tokens: int,
    temperature: float,
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    フォールバックプロバイダーを使用して処理を試みる関数

    Args:
        messages: メッセージのリスト
        primary_provider: 最初に使用するプロバイダー
        primary_model: 最初に使用するモデル
        max_tokens: 最大トークン数
        temperature: 温度
        additional_params: 追加パラメータ

    Returns:
        (レスポンス, 使用したプロバイダー, 使用したモデル)のタプル
    """
    # 最初のプロバイダーを試す
    try:
        response = await call_model_with_retry(
            messages=messages,
            model_name=primary_model,
            provider_name=primary_provider,
            max_tokens=max_tokens,
            temperature=temperature,
            additional_params=additional_params
        )
        return response, primary_provider, primary_model
    except (LiteLLMAPIError, LiteLLMTimeoutError, LiteLLMRateLimitError, ModelNotAvailableError) as e:
        logger.warning(f"Primary provider {primary_provider} failed: {e}")

    # フォールバックプロバイダーが設定されていない場合はそのままエラーを発生
    if not settings.FALLBACK_PROVIDERS:
        raise LiteLLMAPIError(f"Primary provider {primary_provider} failed and no fallback providers configured")

    # フォールバックプロバイダーを順番に試す
    for fallback_provider in settings.FALLBACK_PROVIDERS:
        # 同じプロバイダーはスキップ
        if fallback_provider == primary_provider:
            continue

        logger.info(f"Trying fallback provider: {fallback_provider}")

        # フォールバック用のモデル名を決定（実装によって最適なモデルを選択できる）
        fallback_model = primary_model
        if fallback_provider != primary_provider:
            # ここで必要に応じてプロバイダーに適したモデルに変更
            # 例: OpenAIのgpt-4-turboに対応するAnthropicのモデルを選ぶなど
            # この実装例では単純化のため同じモデル名を使用
            pass

        try:
            response = await call_model_with_retry(
                messages=messages,
                model_name=fallback_model,
                provider_name=fallback_provider,
                max_tokens=max_tokens,
                temperature=temperature,
                additional_params=additional_params
            )
            return response, fallback_provider, fallback_model
        except (LiteLLMAPIError, LiteLLMTimeoutError, LiteLLMRateLimitError, ModelNotAvailableError) as e:
            logger.warning(f"Fallback provider {fallback_provider} failed: {e}")

    # すべてのフォールバックが失敗
    raise LiteLLMAPIError("All providers failed")

async def call_model_with_router(
    messages: List[Dict[str, str]],
    model_alias: str,
    max_tokens: int,
    temperature: float,
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    LiteLLM Routerを使用してモデルを呼び出す関数

    Args:
        messages: メッセージのリスト
        model_alias: モデルのエイリアス (provider/model形式)
        max_tokens: 最大トークン数
        temperature: 温度
        additional_params: 追加パラメータ

    Returns:
        レスポンス
    """
    # Routerインスタンスを取得
    router_manager = get_router()
    if not router_manager.is_enabled():
        # Routerが初期化されていない場合は初期化
        init_router_from_db()

    router = router_manager.get_router()
    if not router:
        raise ModelNotAvailableError("Router not initialized")

    # providerとmodel名を抽出
    provider, model = parse_model_name(model_alias)
    
    # モデルごとに適切な設定を取得
    try:
        # モデル定義から設定を取得
        api_key = None
        base_url = None
        
        # ルーターのモデルリストからAPIキーとエンドポイントを探す
        for model_config in router.model_list:
            if model_config.get("model_name") == model_alias:
                api_key = model_config.get("litellm_params", {}).get("api_key")
                base_url = model_config.get("litellm_params", {}).get("base_url")
                break
        
        if not api_key:
            logger.warning(f"APIキーが見つかりません: {model_alias}")
            
        # パラメータ設定
        response_params = {
            "model": model,  # プロバイダなしのモデル名
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # APIキーを設定
        if api_key:
            response_params["api_key"] = api_key
            
        # base_urlを設定（Ollamaは必須、その他は明示的に指定がある場合のみ）
        if provider.lower() == "ollama":
            # Ollamaの場合はエンドポイント必須
            if base_url:
                logger.info(f"Ollamaのエンドポイント設定: {base_url}")
                response_params["base_url"] = base_url
            else:
                logger.warning(f"Ollamaはエンドポイント指定が必須です")
        elif base_url:
            # その他のプロバイダは明示的に指定がある場合のみ設定
            logger.info(f"カスタムエンドポイント設定: {base_url}")
            response_params["base_url"] = base_url
        else:
            # エンドポイント設定なし - LiteLLMのデフォルト動作に任せる
            logger.info(f"{provider}/{model}はデフォルトエンドポイントを使用")
            
        # 追加パラメータの適用
        if additional_params:
            response_params.update(additional_params)
            
        # 安全にログ出力（APIキーを隠す）
        safe_params = response_params.copy()
        if "api_key" in safe_params:
            api_key = safe_params["api_key"]
            if len(api_key) > 7:
                safe_params["api_key"] = f"{api_key[:4]}...{api_key[-4:]}"
                
        logger.info(f"LLM呼び出しパラメータ: {safe_params}")
        
        # litellm.acompletionを使用してLLMを呼び出し
        logger.info(f"LiteLLMを使用してLLM呼び出し: {provider}/{model}")
        
        # モデル形式の調整: Ollamaの場合のみprovider/model形式を使用
        if provider.lower() == "ollama":
            # Ollamaの場合は provider/model 形式が必要
            response_params["model"] = f"{provider}/{model}"
            logger.info(f"Ollamaのためモデル名をprovider/model形式に調整: {response_params['model']}")
        else:
            # その他のプロバイダの場合はモデル名のみを使用
            response_params["model"] = model
            logger.info(f"モデル名をモデル名のみに調整: {response_params['model']}")
        
        # プロバイダを明示的に設定
        response_params["provider"] = provider
        
        try:
            # 非同期で呼び出し
            response = await litellm.acompletion(**response_params)
            logger.info(f"LLM呼び出し成功: レスポンスID={response.id}")
        except Exception as e:
            logger.error(f"LLM呼び出しエラー: {e}")
            
            # エラーの詳細情報を取得
            error_details = str(e)
            
            # APIキーをマスク
            if "api_key" in error_details and api_key:
                masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 7 else "[masked]"
                error_details = error_details.replace(api_key, masked_key)
            
            # 特定のエラータイプに応じた詳細情報
            if "404 Not Found" in error_details:
                # URLエラーの可能性
                logger.error(f"URLエラー検出: 404 Not Found")
                logger.error(f"設定されたbase_url: {response_params.get('base_url')}")
                
                # プロバイダ別のアドバイス
                logger.error(f"プロバイダの正しいエンドポイントを設定してください:")
                logger.error(f"- OpenAIの場合は、エンドポイントが 'https://api.openai.com/v1' であるか確認してください")
                logger.error(f"- Anthropicの場合は、エンドポイントが 'https://api.anthropic.com' であるか確認してください")
                logger.error(f"- Ollamaの場合は、正しいホストとポート (例: 'http://localhost:11434') を指定してください")
            
            logger.error(f"詳細エラー: {error_details}")
            raise
        
        return {
            "response": response,
            "provider": provider,
            "model": model
        }
    
    except Exception as e:
        # 例外発生時は通常のルーター処理にフォールバック
        logger.warning(f"Error when using direct model access, falling back to router: {e}")
        # モデル名の調整（Ollamaの場合のみprovider/model形式）
        adjusted_model = None
        if provider.lower() == "ollama":
            # Ollamaはprovider/model形式を保持
            adjusted_model = model_alias
        else:
            # その他のプロバイダはmodel名のみを使用
            adjusted_model = model
        
        logger.info(f"ルーター用にモデル名を調整: {model_alias} -> {adjusted_model}")
        
        # リクエストパラメータの設定
        request_params = {
            "model": adjusted_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # 追加パラメータの適用
        if additional_params:
            request_params.update(additional_params)
            
        # リクエストパラメータのデバッグログ（APIキーを隠す）
        safe_params = request_params.copy()
        if 'api_key' in safe_params:
            api_key = safe_params['api_key']
            if len(api_key) > 7:
                safe_params['api_key'] = f"{api_key[:4]}...{api_key[-4:]}"
        logger.info(f"ルーター呼び出しパラメータ: {safe_params}")

        try:
            # Routerを使用してAPI呼び出し
            logger.info(f"RouterでLLM呼び出し: {model_alias}")
            response = await router.acompletion(**request_params)
            logger.info(f"ルーター呼び出し成功: {model_alias}")

            # 使用されたモデル情報を取得
            model_info = response.get("model_info", {})

            return {
                "response": response,
                "provider": model_info.get("provider", provider),
                "model": model_info.get("model", model)
            }
        except asyncio.TimeoutError:
            logger.warning(f"Timeout calling model via router: {model_alias}")
            raise LiteLLMTimeoutError(f"Timeout calling model via router: {model_alias}")
        except Exception as e:
            error_message = str(e).lower()
            if "rate limit" in error_message or "too many requests" in error_message:
                logger.warning(f"Rate limit error: {e}")
                raise LiteLLMRateLimitError(f"Rate limit error: {str(e)}")
            else:
                logger.error(f"Error calling model via router: {e}")
                raise LiteLLMAPIError(f"API error: {str(e)}")

async def call_model_with_litellm(
    messages: List[Dict[str, str]],
    model_name: str,
    provider_name: str,
    max_tokens: int = settings.DEFAULT_MAX_TOKENS,
    temperature: float = settings.DEFAULT_TEMPERATURE,
    additional_params: Optional[Dict[str, Any]] = None,
    use_fallback: bool = True,
    use_router: bool = True
) -> Dict[str, Any]:
    """
    LiteLLMを使用してモデルを呼び出す関数

    Args:
        messages: メッセージのリスト
        model_name: モデル名
        provider_name: プロバイダ名
        max_tokens: 最大トークン数
        temperature: 温度
        additional_params: 追加パラメータ辞書
        use_fallback: フォールバックプロバイダーを使用するかどうか
        use_router: LiteLLM Routerを使用するかどうか

    Returns:
        (モデルの出力テキスト、使用したプロバイダー、使用したモデル)の辞書
    """
    try:
        # Routerが有効で使用可能かチェック
        router_enabled = False
        if use_router:
            router_manager = get_router()
            router_enabled = router_manager.is_enabled()

        if router_enabled:
            # LiteLLM Routerを使用
            logger.info(f"Using LiteLLM Router for model: {model_name}")

            # モデルエイリアスの作成（表示名またはプロバイダ/モデル形式）
            model_alias = format_litellm_model_name(provider_name, model_name)

            result = await call_model_with_router(
                messages=messages,
                model_alias=model_alias,
                max_tokens=max_tokens,
                temperature=temperature,
                additional_params=additional_params
            )

            # レスポンスの内容を取得
            response = result["response"]
            used_provider = result["provider"]
            used_model = result["model"]
        elif use_fallback and settings.FALLBACK_PROVIDERS:
            # フォールバックロジックを使用
            response, used_provider, used_model = await try_fallback_providers(
                messages=messages,
                primary_provider=provider_name,
                primary_model=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                additional_params=additional_params
            )
        else:
            # リトライロジックを含む関数を呼び出し（フォールバックなし）
            response = await call_model_with_retry(
                messages=messages,
                model_name=model_name,
                provider_name=provider_name,
                max_tokens=max_tokens,
                temperature=temperature,
                additional_params=additional_params
            )
            used_provider = provider_name
            used_model = model_name

        return {
            "content": response.choices[0].message.content,
            "provider": used_provider,
            "model": used_model
        }

    except (LiteLLMAPIError, LiteLLMTimeoutError, LiteLLMRateLimitError, ModelNotAvailableError) as e:
        logger.error(f"Failed after retries: {e}")
        return {
            "content": f"ERROR: {str(e)}",
            "provider": provider_name,
            "model": model_name
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "content": f"ERROR: Unexpected error occurred: {str(e)}",
            "provider": provider_name,
            "model": model_name
        }

async def process_batch(batch: List[Dict], model_name: str, provider_name: str,
                       instruction: str, output_length: int, n_shots: int, dataset_name: str,
                       additional_params: Optional[Dict[str, Any]] = None):
    """
    バッチ処理を行う関数

    Args:
        batch: サンプルのバッチ
        model_name: モデル名
        provider_name: プロバイダ名
        instruction: タスクの指示
        output_length: 出力の最大長
        n_shots: Few-shotサンプル数
        dataset_name: データセット名
        additional_params: 追加パラメータ辞書

    Returns:
        処理結果のリスト
    """
    few_shots = await get_few_shot_samples(dataset_name, n_shots)
    results = []

    for sample in batch:
        messages = await format_prompt(instruction, sample["input"], few_shots)
        response = await call_model_with_litellm(
            messages=messages,
            model_name=model_name,
            provider_name=provider_name,
            max_tokens=output_length,
            additional_params=additional_params
        )

        # 出力の前処理（テキスト整形など）
        raw_output = response["content"]
        processed_output = raw_output.strip()
        # 必要に応じて、さらに処理を追加

        results.append({
            "input": sample["input"],
            "expected_output": sample["output"],
            "raw_output": raw_output,
            "processed_output": processed_output,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "provider": response["provider"],  # 使用したプロバイダー
            "model": response["model"]         # 使用したモデル
        })

    return results

async def run_evaluation(
    dataset_name: str,
    provider_name: str,
    model_name: str,
    num_samples: int,
    n_shots: List[int],
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    評価の実行プロセス

    Args:
        dataset_name: 評価対象のデータセット名
        provider_name: モデルのプロバイダ名
        model_name: モデル名
        num_samples: 評価するサンプル数
        n_shots: Few-shotサンプル数のリスト
        additional_params: 追加パラメータ辞書

    Returns:
        評価結果を含む辞書
    """
    # データセット名からパスを合成
    # もしdataset_nameが既にパスの場合（例：datasets/test/aio_1）は、ファイル名部分だけを抽出
    if '/' in dataset_name:
        # パスが含まれている場合はそのまま使用
        if dataset_name.endswith('.json'):
            # 完全なパスとして扱う
            dataset_path = Path(dataset_name)
        else:
            # パスが含まれているが拡張子がない場合
            dataset_path = Path(f"{dataset_name}.json")
        base_name = dataset_name.split('/')[-1]
        if base_name.endswith('.json'):
            base_name = base_name[:-5]  # .jsonを削除
    else:
        # データセット名のみの場合
        base_name = dataset_name
        # 絶対パスで生成
        dataset_path = settings.TEST_DATASETS_DIR / f"{base_name}.json"
    
    logger.info(f"Looking for dataset at: {dataset_path}")
    batch_size = settings.BATCH_SIZE

    with dataset_path.open(encoding="utf-8") as f:
        dataset = json.load(f)

    # メトリクス定義の取得（旧形式と新形式の両方をサポート）
    metrics_from_dataset = dataset["metrics"]
    
    # メトリクス名とパラメータのマッピングを作成
    metrics = []
    metrics_parameters = {}
    
    # 旧形式（文字列のリスト）と新形式（辞書のリスト）の両方をサポート
    for metric_item in metrics_from_dataset:
        if isinstance(metric_item, str):
            # 旧形式: 文字列のみ
            metrics.append(metric_item)
        elif isinstance(metric_item, dict) and "name" in metric_item:
            # 新形式: 名前とパラメータを持つ辞書
            metric_name = metric_item["name"]
            metrics.append(metric_name)
            if "parameters" in metric_item and metric_item["parameters"]:
                metrics_parameters[metric_name] = metric_item["parameters"]
    
    instruction = dataset["instruction"]
    output_length = dataset["output_length"]
    samples = dataset["samples"][:num_samples]

    all_results = {}

    for shot in n_shots:
        shot_results = []

        for i in range(0, len(samples), batch_size):
            batch = samples[i:i+batch_size]
            batch_results = await process_batch(
                batch=batch,
                model_name=model_name,
                provider_name=provider_name,
                instruction=instruction,
                output_length=output_length,
                n_shots=shot,
                dataset_name=dataset_name,
                additional_params=additional_params
            )
            shot_results.extend(batch_results)

        # プロバイダー別にカウント
        providers_used = {}
        for result in shot_results:
            used_provider = result.get("provider", provider_name)
            providers_used[used_provider] = providers_used.get(used_provider, 0) + 1

        # プロバイダー使用状況のログ
        for provider, count in providers_used.items():
            percentage = (count / len(shot_results)) * 100
            logger.info(f"Provider {provider} used for {count}/{len(shot_results)} samples ({percentage:.2f}%)")

        error_count = sum(1 for result in shot_results if result["processed_output"].startswith("ERROR:"))
        if error_count > 0:
            logger.warning(f"{error_count} out of {len(shot_results)} samples failed with errors")

        # パラメータを使用してメトリクス関数を取得
        metrics_func_map = get_metrics_functions(metrics_parameters)
        
        for metric_name in metrics:
            if metric_name in metrics_func_map:
                metric_func = metrics_func_map[metric_name]
                scores = [
                    metric_func(result["processed_output"], result["expected_output"])
                    for result in shot_results if not result["processed_output"].startswith("ERROR:")
                ]
                if scores:  # エラーを除いたスコアがある場合のみ平均を計算
                    avg_score = sum(scores) / len(scores)
                    all_results[f"{base_name}_{shot}shot_{metric_name}"] = avg_score
                    
                    # パラメータ情報も記録（あれば）
                    if metric_name in metrics_parameters:
                        all_results[f"{base_name}_{shot}shot_{metric_name}_parameters"] = metrics_parameters[metric_name]
                else:
                    all_results[f"{base_name}_{shot}shot_{metric_name}"] = 0
            else:
                logger.warning(f"Metric '{metric_name}' specified in dataset but not found in registry")

        all_results[f"{base_name}_{shot}shot_details"] = shot_results

    summary = []
    for shot in n_shots:
        row = {
            "dataset": dataset_name,
            "model": f"{provider_name}/{model_name}",
            "n_shots": shot,
            "num_samples": len(samples)
        }
        # all_results のキーから実際に測定された指標だけ追加
        prefix = f"{base_name}_{shot}shot_"
        for key, value in all_results.items():
            if key.startswith(prefix) and not key.endswith("_details"):
                metric_name = key[len(prefix):]
                row[metric_name] = value
        summary.append(row)

    return {
        "summary": summary,       # DataFrame ではなく List[Dict]
        "details": all_results,
        "metadata": {
            "dataset": dataset_name,
            "model": f"{provider_name}/{model_name}",
            "num_samples": num_samples,
            "n_shots": n_shots,
            "timestamp": datetime.datetime.now().isoformat()
        }
    }

async def run_multiple_evaluations(
    datasets: List[str],
    provider_name: str,
    model_name: str,
    num_samples: int,
    n_shots: List[int],
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    複数データセットに対する評価を実行する関数

    Args:
        datasets: 評価するデータセットのリスト
        provider_name: プロバイダ名
        model_name: モデル名
        num_samples: 評価するサンプル数
        n_shots: Few-shotサンプル数のリスト
        additional_params: 追加パラメータ辞書

    Returns:
        評価結果の辞書
    """
    results = {}
    all_summary: List[Dict[str, Any]] = []
    timestamp = datetime.datetime.now().isoformat()

    # ルーターが初期化されていない場合は初期化
    router_manager = get_router()
    if not router_manager.is_enabled():
        logger.info("Initializing LiteLLM Router for evaluation")
        init_router_from_db()

    for dataset_name in datasets:
        dataset_results = await run_evaluation(
            dataset_name, provider_name, model_name, num_samples, n_shots, additional_params
        )
        results[dataset_name] = dataset_results
        # 辞書リストをそのままマージ
        all_summary.extend(dataset_results["summary"])

    return {
        "results": results,
        "summary": all_summary,   # List[Dict]
        "metadata": {
            "provider_name": provider_name,
            "model_name": model_name,
            "datasets": datasets,
            "num_samples": num_samples,
            "n_shots": n_shots,
            "timestamp": timestamp,
            "additional_params": additional_params
        }
    }

def save_results_as_json(results: Dict[str, Any], provider_name: str, model_name: str) -> Path:
    """
    評価結果をJSONファイルとして保存する関数

    Args:
        results: 評価結果辞書
        provider_name: プロバイダ名
        model_name: モデル名

    Returns:
        保存したファイルのパス
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{provider_name}_{model_name}_{timestamp}.json"
    file_path = settings.RESULTS_DIR / filename

    # pandas 不要。results["summary"] は List[Dict] のまま
    json_results = {
        "summary": results["summary"],
        "metadata": results["metadata"],
        "datasets": {}
    }
    for ds, ds_res in results["results"].items():
        json_results["datasets"][ds] = {
            "metadata": ds_res["metadata"],
            "details": ds_res["details"]
        }

    with file_path.open("w", encoding="utf-8") as f:
        json.dump(json_results, f, ensure_ascii=False, indent=2)

    logger.info(f"Results saved to {file_path}")
    return file_path


async def main():
    """
    メイン関数
    """
    # 評価設定 - 設定からデフォルト値を使用
    provider_name = settings.DEFAULT_PROVIDER
    model_name = "phi4:latest"
    datasets = ["aio", "janli"]  # 評価するデータセット
    num_samples = settings.DEFAULT_NUM_SAMPLES  # 評価するサンプル数
    n_shots = settings.DEFAULT_N_SHOTS  # Few-shotサンプル数

    # LiteLLM Routerを初期化
    init_router_from_db()

    # 追加パラメータ（例：カスタムヘッダー）
    additional_params = {
        "headers": {"User-Agent": "LLM-Evaluation-Tool/1.0"}
    }

    # 利用可能なメトリクスを表示
    logger.info(f"Available metrics: {list(METRICS_FUNC_MAP.keys())}")

    logger.info(f"Starting evaluation: {provider_name}/{model_name}")
    logger.info(f"Datasets: {datasets}")
    logger.info(f"Number of samples: {num_samples}")
    logger.info(f"Number of shots: {n_shots}")

    # 評価の実行
    results = await run_multiple_evaluations(
        datasets=datasets,
        provider_name=provider_name,
        model_name=model_name,
        num_samples=num_samples,
        n_shots=n_shots,
        additional_params=additional_params
    )

    # 結果の保存
    results_file = save_results_as_json(results, provider_name, model_name)
    logger.info(f"Evaluation completed. Results saved to {results_file}")

if __name__ == "__main__":
    asyncio.run(main())
