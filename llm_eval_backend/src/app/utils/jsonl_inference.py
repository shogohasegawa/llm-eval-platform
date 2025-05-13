"""
JSONLフォーマットのマルチターン会話データセットに対する推論処理モジュール
このモジュールでは、MT-Benchのようなマルチターン会話データセット（JSONLフォーマット）に対する
推論処理機能を提供します。
"""
import json
import logging
import os
import time
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.utils.multi_turn_inference import Conversation
from app.utils.litellm_helper import get_provider_options
from app.config.config import get_settings

from litellm import acompletion

# 設定の取得
settings = get_settings()

# ロギングの設定
logger = logging.getLogger(__name__)


async def load_jsonl_dataset(file_path: str) -> List[Dict]:
    """JSONLファイルからデータセットを読み込む

    Args:
        file_path: JSONLファイルのパス

    Returns:
        データセットの質問リスト
    """
    questions = []
    try:
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    q = json.loads(line)
                    questions.append(q)
        logger.info(f"JSONLデータセットを読み込みました: {file_path}, {len(questions)}件の質問")
        return questions
    except Exception as e:
        logger.error(f"JSONLデータセットの読み込みに失敗しました: {file_path}, エラー: {e}")
        return []


async def run_inference_on_jsonl(
    dataset_path: str,
    provider_name: str,
    model_name: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    num_samples: int = None,
    system_message: str = "You are a helpful assistant.",
) -> Dict[str, Any]:
    """JSONLデータセットに対して推論を実行する

    Args:
        dataset_path: データセットのファイルパス
        provider_name: プロバイダ名
        model_name: モデル名
        max_tokens: 最大トークン数
        temperature: 温度
        num_samples: 実行するサンプル数（Noneなら全て）
        system_message: システムメッセージ

    Returns:
        推論結果
    """
    # プロバイダーとモデル名の組み合わせ
    full_model_name = f"{provider_name}/{model_name}"
    logger.info(f"JSONLデータセット推論開始: {dataset_path}, モデル: {full_model_name}")

    # JSONLデータセットの読み込み
    questions = await load_jsonl_dataset(dataset_path)
    if not questions:
        return {"error": "データセットの読み込みに失敗しました"}

    # サンプル数の制限（指定があれば）
    if num_samples is not None and num_samples > 0 and num_samples < len(questions):
        questions = questions[:num_samples]
        logger.info(f"サンプル数を{num_samples}件に制限しました")

    # 結果用の辞書
    results = {
        "dataset_path": dataset_path,
        "model": full_model_name,
        "timestamp": time.time(),
        "questions": []
    }

    # プロバイダー固有のオプションを取得
    additional_params = get_provider_options(provider_name)

    # 各質問に対して推論を実行
    for question in questions:
        question_id = question.get("question_id", str(uuid.uuid4()))
        category = question.get("category", "unknown")
        turns = question.get("turns", [])

        if not turns:
            logger.warning(f"質問ID {question_id} にターンデータがありません")
            continue

        # 会話コンテキストを初期化
        conv = Conversation(system_message=system_message)

        # 各ターンに対して推論を実行
        turn_results = []
        logger.info(f"質問ID {question_id}, カテゴリ: {category}, ターン数: {len(turns)}")

        for i, turn in enumerate(turns):
            # ユーザー発言を追加
            conv.append_message(conv.roles[0], turn)
            # アシスタント応答のプレースホルダーを追加
            conv.append_message(conv.roles[1], None)

            # 推論リクエストの準備
            messages = conv.to_openai_api_messages()
            
            try:
                # LiteLLMのacompletionを使用して推論
                start_time = time.time()

                # プロバイダとモデル情報の詳細ログ出力
                logger.info(f"推論実行: プロバイダ={provider_name}, モデル={model_name}")
                # APIキーを含む可能性のあるパラメータはログに出力しない
                safe_params = {k: v for k, v in additional_params.items() if k != "api_key"}
                logger.info(f"追加パラメータ: {safe_params}")

                # プロバイダモデル設定情報を直接取得
                from app.utils.db.models import get_model_repository
                from app.utils.db.providers import get_provider_repository

                # モデルとプロバイダの情報を取得
                model_repo = get_model_repository()
                provider_repo = get_provider_repository()

                # プロバイダIDを先に取得
                providers = provider_repo.get_all_providers()
                provider_id = None
                for p in providers:
                    if p["type"] == provider_name or p["name"] == provider_name:
                        provider_id = p["id"]
                        logger.info(f"プロバイダID取得: {provider_id} ({p['name']})")
                        break

                # モデルを取得
                models = model_repo.get_all_models()
                api_key = None
                for m in models:
                    if m["name"] == model_name and (not provider_id or m["provider_id"] == provider_id):
                        # APIキーをモデルから取得
                        api_key = m.get("api_key")
                        logger.info(f"モデルAPIキー: {'取得成功' if api_key else '未設定'}")
                        break

                # プロバイダからAPIキーを取得（モデルにキーがない場合）
                if not api_key and provider_id:
                    provider = provider_repo.get_provider_by_id(provider_id)
                    if provider:
                        api_key = provider.get("api_key")
                        logger.info(f"プロバイダAPIキー: {'取得成功' if api_key else '未設定'}")

                # APIキーを設定（直接渡す）
                if api_key:
                    additional_params["api_key"] = api_key
                    # APIキーの末尾数桁のみをログに出力（セキュリティ対策）
                    if len(api_key) > 8:
                        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
                        logger.info(f"APIキーを明示的に設定しました: {masked_key}")
                    else:
                        logger.info(f"APIキーを明示的に設定しました")

                response = await acompletion(
                    model=f"{provider_name}/{model_name}",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **additional_params
                )
                end_time = time.time()
                
                # 応答テキストの取得
                output = response.choices[0].message.content
                latency = end_time - start_time

                # 会話コンテキストを更新
                conv.update_last_message(output)

                turn_results.append({
                    "turn_idx": i,
                    "user_input": turn,
                    "model_output": output,
                    "latency": latency
                })

                # 詳細なログ出力（質問と回答の内容）
                logger.info(f"質問ID {question_id}, ターン {i+1}/{len(turns)} 完了, レイテンシ: {latency:.2f}秒")
                logger.info(f"質問: {turn}")
                logger.info(f"回答: {output}")
            
            except Exception as e:
                logger.error(f"推論中にエラーが発生しました: 質問ID {question_id}, ターン {i+1}, エラー: {e}")
                # エラー情報を保存
                turn_results.append({
                    "turn_idx": i,
                    "user_input": turn,
                    "model_output": f"ERROR: {str(e)}",
                    "error": str(e)
                })
                break

        # 質問全体の結果を保存
        results["questions"].append({
            "question_id": question_id,
            "category": category,
            "turns": turn_results
        })

    # 統計情報を追加
    results["total_questions"] = len(results["questions"])
    results["completed_questions"] = sum(1 for q in results["questions"] if len(q["turns"]) == len(questions[0].get("turns", [])))
    
    return results


async def save_jsonl_inference_results(results: Dict[str, Any], output_dir: str = None) -> str:
    """推論結果をJSONファイルとして保存する

    Args:
        results: 推論結果
        output_dir: 出力ディレクトリ（Noneならデフォルト）

    Returns:
        保存されたファイルのパス
    """
    if output_dir is None:
        output_dir = str(settings.RESULTS_DIR)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # ファイル名を生成
    timestamp = int(time.time())
    dataset_name = os.path.basename(results["dataset_path"]).replace(".jsonl", "")
    model_name = results["model"].replace("/", "_")
    filename = f"{dataset_name}_{model_name}_{timestamp}.json"
    file_path = os.path.join(output_dir, filename)
    
    # 結果をJSONファイルとして保存
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"推論結果を保存しました: {file_path}")

    # 保存した結果の要約をログに出力
    total_questions = len(results["questions"])
    total_turns = sum(len(q.get("turns", [])) for q in results["questions"])
    logger.info(f"推論結果の要約: {total_questions}件の質問に対して合計{total_turns}ターンの会話を処理しました")
    logger.info(f"総合結果: 完了した質問数 {results.get('completed_questions', 0)}/{results.get('total_questions', 0)}")

    return file_path