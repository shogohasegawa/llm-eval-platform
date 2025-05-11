"""
バッチ推論を効率的に処理するためのモジュール

LiteLLMのbatch_completion機能を使用して、複数のサンプルを効率的にバッチ処理します。

TODO:
- LiteLLMのbatch_completionとacompletionのAPIキー処理の違いを調査する
- バッチ処理とシングル処理のログ出力を強化し、APIキーの処理過程を詳細に記録する
- LiteLLMのドキュメントを確認し、batch_completionとacompletionの動作の違いを把握する
- バッチ処理のパフォーマンス測定と最適化（処理時間、スループット、エラー率など）を行う
"""
from typing import List, Dict, Any, Optional
import asyncio
import logging
import litellm
from litellm import batch_completion
from app.config import get_settings
from app.utils.litellm_helper import get_provider_options, validate_api_key, get_api_key_error_message, format_litellm_model_name

# 設定の取得
settings = get_settings()

# ロギングの設定
logger = logging.getLogger(__name__)


async def process_batch_efficiently(
    batch: List[Dict],
    model_name: str,
    provider_name: str,
    instruction: str,
    output_length: int,
    few_shots: List[Dict[str, str]],
    additional_params: Optional[Dict[str, Any]] = None
) -> List[Dict]:
    """
    LiteLLMのbatch_completion機能を使用して、バッチ内のサンプルを効率的に処理します。

    Args:
        batch: 処理するサンプルのバッチ
        model_name: モデル名
        provider_name: プロバイダ名
        instruction: タスクの指示
        output_length: 出力の最大長
        few_shots: Few-shotサンプルのリスト
        additional_params: 追加パラメータ辞書

    Returns:
        処理結果のリスト
    """
    logger.info(f"バッチ処理開始: {len(batch)}サンプル")

    # 各サンプルのメッセージを準備
    all_messages = []

    # システムメッセージの作成
    is_english = "mmlu_en" in instruction
    if is_english:
        message_intro = "The following text provides instructions for a certain task."
    else:
        message_intro = "以下に、あるタスクを説明する指示があり、それに付随する入力が更なる文脈を提供しています。リクエストを適切に完了するための回答を記述してください。"

    system_message = f"{message_intro}\n\n{instruction}"

    # 各サンプルのプロンプトを作成
    for sample in batch:
        # サンプルごとのメッセージ
        messages = []

        # システムメッセージを追加
        messages.append({"role": "system", "content": system_message})

        # Few-shotサンプルの追加
        if few_shots:
            messages.extend(few_shots)

        # ユーザー入力の追加
        messages.append({"role": "user", "content": sample.get("input", "")})

        # このサンプルのメッセージをリストに追加
        all_messages.append(messages)

    # バッチ処理を有効にするプロバイダをホワイトリストで設定
    batch_supported_providers = ['openai', 'anthropic', 'claude', 'cohere', 'together', 'groq']

    if provider_name.lower() not in batch_supported_providers:
        # サポートされていないプロバイダの場合は早期リターン
        logger.warning(f"{provider_name}プロバイダではLiteLLMのbatch_completionに互換性の問題があるため、バッチ処理をスキップします")
        raise ValueError(f"{provider_name}プロバイダではバッチ処理はサポートされていません")

    # サポートされたプロバイダの場合は通常通り処理
    full_model_name = format_litellm_model_name(provider_name, model_name)

    # ベースパラメータの準備
    params = {
        "model": full_model_name,
        "messages": all_messages,
        "max_tokens": output_length,
    }

    # プロバイダ固有の設定を取得し、APIキーとベースURLを設定
    provider_options = get_provider_options(provider_name)
    if provider_options:
        # APIキーの設定
        if "api_key" in provider_options:
            api_key = provider_options["api_key"]
            # APIキーを検証
            if validate_api_key(api_key, provider_name):
                # 有効なAPIキーの場合
                params["api_key"] = api_key
                if len(api_key) > 7:
                    masked_key = f"{api_key[:4]}...{api_key[-4:]}"
                    logger.info(f"バッチ処理用APIキー設定: {masked_key}")
            else:
                logger.error(f"無効なAPIキー: {api_key[:4]}... バッチ処理は失敗する可能性があります")

        # ベースURLの設定
        if "base_url" in provider_options:
            params["base_url"] = provider_options["base_url"]
            logger.info(f"バッチ処理用ベースURL設定: {provider_options['base_url']}")

        # カスタムヘッダーの設定
        if "headers" in provider_options:
            params["headers"] = provider_options["headers"]

    # 追加パラメータの適用（ただしAPIキーはオーバーライドされないように注意）
    if additional_params:
        # API KEYとベースURLは既に設定されている場合はオーバーライドしない
        safe_params = additional_params.copy()
        if "api_key" in params and "api_key" in safe_params:
            del safe_params["api_key"]
        if "base_url" in params and "base_url" in safe_params:
            del safe_params["base_url"]
        params.update(safe_params)

    # デバッグログ - APIキーをマスクして表示
    safe_log_params = params.copy()
    if "api_key" in safe_log_params:
        api_key = safe_log_params["api_key"]
        if len(api_key) > 7:
            safe_log_params["api_key"] = f"{api_key[:4]}...{api_key[-4:]}"
    logger.info(f"バッチ処理パラメータ: {safe_log_params}")

    try:
        # バッチ処理を実行
        logger.info(f"LiteLLM batch_completion呼び出し: {full_model_name}, {len(batch)}サンプル")

        # APIキーのログ出力（デバッグ用）
        if "api_key" in params:
            api_key = params["api_key"]
            logger.error(f"BATCH EVALUATION USING API KEY: {api_key} (type: {type(api_key)})")
            if api_key.startswith("sk-your"):
                logger.error(f"BATCH EVAL: デモキー検出! APIキーはデモキー（'sk-your'で始まる）です")

        responses = batch_completion(**params)
        logger.info(f"バッチ処理完了: {len(responses)}応答を受信")

        # 結果を処理
        results = []
        for i, (sample, response) in enumerate(zip(batch, responses)):
            if hasattr(response, 'choices') and len(response.choices) > 0:
                # 正常な応答の処理
                raw_output = response.choices[0].message.content
                processed_output = raw_output.strip()

                # レスポンスのプロバイダとモデル情報を取得
                provider = provider_name
                model = model_name
                if hasattr(response, 'model'):
                    # モデル情報がある場合はそれを使用
                    model_parts = response.model.split('/')
                    if len(model_parts) > 1:
                        provider = model_parts[0]
                        model = model_parts[1]
                    else:
                        model = response.model

                # メッセージ情報を保存
                messages = all_messages[i]

                result_dict = {
                    "input": sample.get("input", ""),
                    "expected_output": sample.get("output", ""),
                    "raw_output": raw_output,
                    "processed_output": processed_output,
                    "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                    "provider": provider,
                    "model": model
                }
            else:
                # エラーまたは無効な応答の処理
                logger.warning(f"サンプル {i+1}/{len(batch)} の応答が無効です: {response}")
                result_dict = {
                    "input": sample.get("input", ""),
                    "expected_output": sample.get("output", ""),
                    "raw_output": f"ERROR: Invalid response",
                    "processed_output": f"ERROR: Invalid response",
                    "messages": [{"role": m["role"], "content": m["content"]} for m in all_messages[i]],
                    "provider": provider_name,
                    "model": model_name
                }

            results.append(result_dict)

        return results
    except Exception as e:
        # エラー処理
        logger.error(f"バッチ処理中にエラーが発生しました: {str(e)}")

        # エラー結果を作成
        error_results = []
        for i, sample in enumerate(batch):
            error_results.append({
                "input": sample.get("input", ""),
                "expected_output": sample.get("output", ""),
                "raw_output": f"ERROR: {str(e)}",
                "processed_output": f"ERROR: {str(e)}",
                "messages": [],
                "provider": provider_name,
                "model": model_name
            })

        return error_results