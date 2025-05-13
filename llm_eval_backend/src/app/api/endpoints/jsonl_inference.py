"""
JSONLデータセット推論API

JSONLフォーマットのマルチターン会話データセット（MT-Benchなど）に対する
推論を実行するAPIエンドポイントを提供します。
"""
import asyncio
import logging
import uuid
import os
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import ValidationError

from app.api.models import JsonlInferenceRequest, JsonlInferenceResponse
from app.utils.jsonl_inference import run_inference_on_jsonl, save_jsonl_inference_results
from app.utils.db.models import get_model_repository
from app.utils.db.providers import get_provider_repository
from app.config.config import get_settings

# ルーター設定
router = APIRouter(prefix="/jsonl-inference", tags=["jsonl-inference"])

# ロガー設定
logger = logging.getLogger(__name__)

# 設定取得
settings = get_settings()

# 実行中のジョブを追跡する辞書（実際の実装では永続化ストレージを使用するべき）
running_jobs: Dict[str, Dict[str, Any]] = {}


@router.post("", response_model=JsonlInferenceResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_jsonl_inference(
    request: JsonlInferenceRequest,
    background_tasks: BackgroundTasks
):
    """JSONLデータセットに対する推論ジョブを作成し、バックグラウンドで実行する

    Args:
        request: 推論リクエスト
        background_tasks: バックグラウンドタスク

    Returns:
        JsonlInferenceResponse: 推論ジョブ情報
    """
    try:
        # プロバイダとモデルの存在確認
        provider_repo = get_provider_repository()
        model_repo = get_model_repository()

        provider = provider_repo.get_provider_by_id(request.provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダID '{request.provider_id}' が見つかりません"
            )

        model = model_repo.get_model_by_id(request.model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{request.model_id}' が見つかりません"
            )

        # ジョブIDを生成
        job_id = str(uuid.uuid4())

        # ジョブ情報を初期化
        job_info = {
            "job_id": job_id,
            "status": "pending",
            "request": request.dict(),
            "provider": provider,
            "model": model,
            "result_file": None
        }
        running_jobs[job_id] = job_info

        # バックグラウンドタスクとして推論を実行
        background_tasks.add_task(
            execute_jsonl_inference,
            job_id=job_id,
            dataset_path=request.dataset_path,
            provider_name=provider["type"],
            model_name=model["name"],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            num_samples=request.num_samples,
            system_message=request.system_message
        )

        # レスポンスを返す
        full_model_name = f"{provider['type']}/{model['name']}"

        # データセットのファイル名（パスから抽出）
        dataset_name = os.path.basename(request.dataset_path)
        logger.info(f"JSONLデータセット推論ジョブを作成しました: {dataset_name}, モデル: {full_model_name}")

        return JsonlInferenceResponse(
            job_id=job_id,
            status="pending",
            message=f"推論ジョブが作成され、バックグラウンドで実行されます: {dataset_name}, モデル: {full_model_name}",
            dataset_path=request.dataset_path,
            model=full_model_name
        )

    except ValidationError as e:
        logger.error(f"入力検証エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"入力検証エラー: {str(e)}"
        )
    except Exception as e:
        logger.error(f"JSONLデータセット推論リクエスト処理エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JSONLデータセット推論リクエスト処理エラー: {str(e)}"
        )


@router.get("/{job_id}", response_model=JsonlInferenceResponse)
async def get_jsonl_inference_status(job_id: str):
    """JSONLデータセット推論ジョブのステータスを取得する

    Args:
        job_id: ジョブID

    Returns:
        JsonlInferenceResponse: 推論ジョブ情報
    """
    try:
        # ジョブ情報を取得
        job_info = running_jobs.get(job_id)
        if not job_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ジョブID '{job_id}' が見つかりません"
            )

        # モデルとプロバイダー情報を取得
        provider = job_info["provider"]
        model = job_info["model"]
        full_model_name = f"{provider['type']}/{model['name']}"

        # ステータスに応じたメッセージを設定
        message = "推論ジョブが実行中です"
        if job_info["status"] == "completed":
            message = "推論ジョブが完了しました"
        elif job_info["status"] == "failed":
            message = f"推論ジョブが失敗しました: {job_info.get('error', 'unknown error')}"

        # 結果ファイルが存在する場合、その内容を取得してログに出力
        result_file = job_info.get("result_file")
        if result_file and job_info["status"] == "completed" and os.path.exists(result_file):
            try:
                # 結果ファイルの内容をログに出力
                with open(result_file, "r", encoding="utf-8") as f:
                    result_data = json.load(f)

                # 結果の要約をログに出力
                total_questions = len(result_data.get("questions", []))
                total_completed = sum(1 for q in result_data.get("questions", [])
                                     if any(not t.get("error") for t in q.get("turns", [])))

                logger.info(f"完了したJSONL推論ジョブの詳細 - ジョブID: {job_id}")
                logger.info(f"データセット: {os.path.basename(job_info['request']['dataset_path'])}")
                logger.info(f"モデル: {full_model_name}")
                logger.info(f"質問数: {total_questions}件, 完了: {total_completed}件")

                # 最初の質問と回答の例を表示（デバッグ用）
                if total_questions > 0 and "questions" in result_data and len(result_data["questions"]) > 0:
                    first_question = result_data["questions"][0]
                    logger.info(f"最初の質問の例 (ID: {first_question.get('question_id')}, カテゴリ: {first_question.get('category', 'なし')})")

                    for i, turn in enumerate(first_question.get("turns", [])):
                        logger.info(f"  ターン {i+1}:")
                        logger.info(f"    質問: {turn.get('user_input', 'なし')}")
                        logger.info(f"    回答: {turn.get('model_output', 'エラー')}")
            except Exception as e:
                logger.error(f"結果ファイルの読み込みに失敗しました: {e}")

        # レスポンスを返す
        return JsonlInferenceResponse(
            job_id=job_id,
            status=job_info["status"],
            message=message,
            dataset_path=job_info["request"]["dataset_path"],
            model=full_model_name,
            result_file=result_file
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSONLデータセット推論ステータス取得エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JSONLデータセット推論ステータス取得エラー: {str(e)}"
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jsonl_inference_job(job_id: str):
    """JSONLデータセット推論ジョブを削除する

    Args:
        job_id: ジョブID
    """
    try:
        # ジョブ情報を確認
        if job_id not in running_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ジョブID '{job_id}' が見つかりません"
            )

        # 実行中のジョブは削除できない
        if running_jobs[job_id]["status"] == "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="実行中のジョブは削除できません"
            )

        # ジョブ情報を削除
        del running_jobs[job_id]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSONLデータセット推論ジョブ削除エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JSONLデータセット推論ジョブ削除エラー: {str(e)}"
        )


async def execute_jsonl_inference(
    job_id: str,
    dataset_path: str,
    provider_name: str,
    model_name: str,
    max_tokens: int,
    temperature: float,
    num_samples: Optional[int],
    system_message: str
):
    """JSONLデータセット推論を実行するバックグラウンドタスク

    Args:
        job_id: ジョブID
        dataset_path: データセットパス
        provider_name: プロバイダ名
        model_name: モデル名
        max_tokens: 最大トークン数
        temperature: 温度
        num_samples: サンプル数
        system_message: システムメッセージ
    """
    # ジョブ情報を更新
    job_info = running_jobs.get(job_id)
    if not job_info:
        logger.error(f"ジョブID '{job_id}' の情報が見つかりません")
        return

    job_info["status"] = "running"
    running_jobs[job_id] = job_info
    
    try:
        # 推論を実行
        logger.info(f"JSONLデータセット推論を開始します: {dataset_path}, {provider_name}/{model_name}")
        
        results = await run_inference_on_jsonl(
            dataset_path=dataset_path,
            provider_name=provider_name,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            num_samples=num_samples,
            system_message=system_message
        )
        
        # 結果をファイルに保存
        result_file = await save_jsonl_inference_results(results)
        
        # ジョブ情報を更新
        job_info["status"] = "completed"
        job_info["result_file"] = result_file
        running_jobs[job_id] = job_info
        
        logger.info(f"JSONLデータセット推論が完了しました: ジョブID {job_id}, 結果ファイル: {result_file}")
    
    except Exception as e:
        # エラー発生時はジョブ情報を更新
        logger.error(f"JSONLデータセット推論実行エラー: {e}", exc_info=True)
        job_info["status"] = "failed"
        job_info["error"] = str(e)
        running_jobs[job_id] = job_info