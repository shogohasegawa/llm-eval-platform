"""
推論管理APIエンドポイント

推論のCRUD操作と実行を提供するエンドポイントを実装します。
"""
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Query, Path

from app.api.models import (
    Inference, 
    InferenceCreate, 
    InferenceUpdate, 
    InferenceStatus, 
    InferenceResult,
    InferenceListResponse,
    InferenceDetailResponse,
    ModelConfig,
    EvaluationRequest
)
from app.utils.db.models import get_model_repository
from app.utils.db.providers import get_provider_repository
from app.utils.db.inferences import get_inference_repository
from app.core.evaluation import run_multiple_evaluations
from app.utils.litellm_helper import get_provider_options

# ロガーの設定
logger = logging.getLogger("llmeval")

router = APIRouter(prefix="/inferences", tags=["inferences"])


@router.get("", response_model=List[Inference])
async def list_inferences(
    dataset_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    model_id: Optional[str] = None,
    status: Optional[str] = None
):
    """
    推論一覧を取得します。
    
    Args:
        dataset_id: データセットIDによるフィルタ
        provider_id: プロバイダIDによるフィルタ
        model_id: モデルIDによるフィルタ
        status: ステータスによるフィルタ
        
    Returns:
        List[Inference]: 推論一覧
    """
    try:
        # フィルター条件を作成
        filters = {}
        if dataset_id:
            filters["dataset_id"] = dataset_id
        if provider_id:
            filters["provider_id"] = provider_id
        if model_id:
            filters["model_id"] = model_id
        if status:
            filters["status"] = status
        
        # リポジトリから推論一覧を取得
        inference_repo = get_inference_repository()
        inferences = inference_repo.get_all_inferences(filters)
        
        # API応答モデルにマッピング
        result = []
        for inf in inferences:
            # 結果を変換
            results = []
            for res in inf.get("results", []):
                results.append(InferenceResult(
                    id=res["id"],
                    inference_id=res["inference_id"],
                    input=res["input"],
                    expected_output=res.get("expected_output"),
                    actual_output=res["actual_output"],
                    metrics=res.get("metrics"),
                    latency=res.get("latency"),
                    token_count=res.get("token_count"),
                    created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
                ))
            
            # 日付文字列をdatetimeに変換
            created_at = datetime.fromisoformat(inf["created_at"]) if isinstance(inf["created_at"], str) else inf["created_at"]
            updated_at = datetime.fromisoformat(inf["updated_at"]) if isinstance(inf["updated_at"], str) else inf["updated_at"]
            completed_at = None
            if inf.get("completed_at"):
                completed_at = datetime.fromisoformat(inf["completed_at"]) if isinstance(inf["completed_at"], str) else inf["completed_at"]
            
            # 推論オブジェクトを作成
            inference = Inference(
                id=inf["id"],
                name=inf["name"],
                description=inf.get("description"),
                dataset_id=inf["dataset_id"],
                provider_id=inf["provider_id"],
                model_id=inf["model_id"],
                status=InferenceStatus(inf["status"]),
                progress=inf["progress"],
                metrics=inf.get("metrics"),
                results=results,
                created_at=created_at,
                updated_at=updated_at,
                completed_at=completed_at,
                error=inf.get("error")
            )
            result.append(inference)
        
        return result
    except Exception as e:
        logger.error(f"推論一覧取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論一覧取得エラー: {str(e)}"
        )


@router.post("", response_model=Inference, status_code=status.HTTP_201_CREATED)
async def create_inference(
    inference_data: InferenceCreate,
    background_tasks: BackgroundTasks
):
    """
    新しい推論を作成し、バックエンドで評価を実行します。
    
    Args:
        inference_data: 作成する推論のデータ
        background_tasks: バックグラウンドタスク
        
    Returns:
        Inference: 作成された推論情報
    """
    try:
        # バリデーション
        if not inference_data.dataset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="データセットIDは必須です"
            )
            
        if not inference_data.provider_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="プロバイダIDは必須です"
            )
            
        if not inference_data.model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="モデルIDは必須です"
            )
            
        # データセット名を抽出（パスからファイル名を取得）
        # "test/example.json" -> "example"
        dataset_name = inference_data.dataset_id.split('/')[-1].replace('.json', '')
        
        # データセットタイプが指定されているか確認
        dataset_type = getattr(inference_data, "dataset_type", None)
        logger.info(f"推論作成: dataset_name={dataset_name}, dataset_type={dataset_type}")
        
        # プロバイダとモデル情報の取得
        provider_repo = get_provider_repository()
        model_repo = get_model_repository()
        
        provider = provider_repo.get_provider_by_id(inference_data.provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダID '{inference_data.provider_id}' が見つかりません"
            )
        
        model = model_repo.get_model_by_id(inference_data.model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{inference_data.model_id}' が見つかりません"
            )
        
        provider_type = provider["type"]
        model_name = model["name"]
        
        # モデル設定を構築
        model_config = ModelConfig(
            provider=provider_type,  
            model_name=model_name,
            max_tokens=inference_data.max_tokens or 512,
            temperature=inference_data.temperature or 0.7,
            top_p=inference_data.top_p or 1.0
        )
        
        # データセットを取得
        from app.utils.dataset.operations import get_dataset_by_name
        dataset_info = None
        
        # データセットタイプが指定されている場合は取得を試みる
        if dataset_type:
            dataset_info = get_dataset_by_name(dataset_name, dataset_type)
            logger.info(f"データセット取得（タイプ指定あり）: {dataset_name}, タイプ: {dataset_type}, 結果: {dataset_info is not None}")
        
        # タイプ指定が無いか取得に失敗した場合は、タイプなしで再試行
        if not dataset_info:
            dataset_info = get_dataset_by_name(dataset_name)
            if dataset_info:
                # 取得できた場合はそのタイプを記録
                dataset_type = dataset_info["metadata"].type
                logger.info(f"データセット取得（タイプ指定なし）: {dataset_name}, 検出タイプ: {dataset_type}")
        
        # それでも取得できない場合はエラー
        if not dataset_info:
            logger.error(f"データセットが見つかりません: {dataset_name}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"データセット '{dataset_name}' が見つかりません"
            )
        
        # 評価リクエストを構築
        evaluation_request = EvaluationRequest(
            datasets=[dataset_name],
            num_samples=inference_data.num_samples or 100,
            n_shots=[inference_data.n_shots or 0],
            model=model_config
        )
        
        logger.info(f"評価リクエスト: {evaluation_request}")
        
        # 新しい推論をデータベースに保存
        inference_repo = get_inference_repository()
        
        # パラメータを保存
        parameters = {
            "max_tokens": inference_data.max_tokens or 512,
            "temperature": inference_data.temperature or 0.7,
            "top_p": inference_data.top_p or 1.0,
            "num_samples": inference_data.num_samples or 100,
            "n_shots": inference_data.n_shots or 0,
            "dataset_type": dataset_type  # データセットタイプを追加
        }
        
        # 推論を作成（初期状態はPENDING）
        inference_db = inference_repo.create_inference({
            "name": inference_data.name,
            "description": inference_data.description,
            "dataset_id": inference_data.dataset_id,
            "provider_id": inference_data.provider_id,
            "model_id": inference_data.model_id,
            "status": InferenceStatus.PENDING,
            "progress": 0,
            "parameters": parameters
        })
        
        # 背景タスクで評価を実行
        background_tasks.add_task(
            execute_inference_evaluation,
            inference_id=inference_db["id"],
            evaluation_request=evaluation_request,
            provider_name=provider_type,
            model_name=model_name
        )
        
        # 結果を変換
        results = []
        for res in inference_db.get("results", []):
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            ))
        
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(inference_db["created_at"]) if isinstance(inference_db["created_at"], str) else inference_db["created_at"]
        updated_at = datetime.fromisoformat(inference_db["updated_at"]) if isinstance(inference_db["updated_at"], str) else inference_db["updated_at"]
        completed_at = None
        if inference_db.get("completed_at"):
            completed_at = datetime.fromisoformat(inference_db["completed_at"]) if isinstance(inference_db["completed_at"], str) else inference_db["completed_at"]
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=inference_db["id"],
            name=inference_db["name"],
            description=inference_db.get("description"),
            dataset_id=inference_db["dataset_id"],
            provider_id=inference_db["provider_id"],
            model_id=inference_db["model_id"],
            status=InferenceStatus(inference_db["status"]),
            progress=inference_db["progress"],
            metrics=inference_db.get("metrics"),
            results=results,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error=inference_db.get("error")
        )
        
        return inference
        
    except Exception as e:
        logger.error(f"推論作成エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論作成エラー: {str(e)}"
        )


# 背景タスクとして実行する評価関数
async def execute_inference_evaluation(
    inference_id: str,
    evaluation_request: EvaluationRequest,
    provider_name: str,
    model_name: str
):
    """
    推論評価を実行するバックグラウンドタスク
    
    Args:
        inference_id: 推論ID
        evaluation_request: 評価リクエスト
        provider_name: プロバイダー名
        model_name: モデル名
    """
    logger.info(f"推論 {inference_id} の評価を開始します")
    inference_repo = get_inference_repository()
    
    try:
        # 推論のステータスを更新（進捗は表示しない）
        inference_repo.update_inference(inference_id, {"status": InferenceStatus.RUNNING, "progress": -1})
        
        # 追加パラメータを準備（プロバイダごとのデフォルト設定を適用）
        additional_params = get_provider_options(provider_name)
        
        # 評価エンジン呼び出し
        results_full = await run_multiple_evaluations(
            datasets=evaluation_request.datasets,
            provider_name=provider_name,
            model_name=model_name,
            num_samples=evaluation_request.num_samples,
            n_shots=evaluation_request.n_shots,
            additional_params=additional_params
        )
        
        # 結果をJSONファイルに保存
        import os
        import time
        results_dir = "/app/results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
            
        timestamp = int(time.time())
        # 推論IDを含むディレクトリを作成
        inference_dir = f"{results_dir}/{inference_id}"
        if not os.path.exists(inference_dir):
            os.makedirs(inference_dir)
            
        # 詳細な結果を含むJSONファイル
        results_filename = f"{inference_dir}/results_{timestamp}.json"
        with open(results_filename, "w", encoding="utf-8") as f:
            json.dump(results_full, f, ensure_ascii=False, indent=2)
            
        # 推論自体の情報も保存
        inference_filename = f"{inference_dir}/inference.json"
        with open(inference_filename, "w", encoding="utf-8") as f:
            inference_info = {
                "inference_id": inference_id,
                "provider": provider_name,
                "model": model_name,
                "timestamp": datetime.now().isoformat(),
                "evaluation_request": evaluation_request.dict(),
                "results_file": results_filename
            }
            json.dump(inference_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"推論結果をJSONファイルに保存しました: {results_filename}")
        logger.info(f"推論情報をJSONファイルに保存しました: {inference_filename}")
        
        # デバッグ用：推論結果ファイルへのアクセスパスを記録
        n_shots_value = evaluation_request.n_shots[0] if evaluation_request.n_shots and len(evaluation_request.n_shots) > 0 else 0
        inference_repo.update_inference(inference_id, {
            "description": f"最新の推論結果ファイル: {results_filename}\nモデル: {provider_name}/{model_name}, n_shots: {n_shots_value}"
        })
        
        # フラットなメトリクス辞書を作成（n_shots情報を含める）
        flat_metrics: Dict[str, Any] = {}
        n_shots_value = evaluation_request.n_shots[0] if evaluation_request.n_shots and len(evaluation_request.n_shots) > 0 else 0
        n_shots_suffix = f"_{n_shots_value}shot"
        
        # 新しいベストプラクティス: n_shots_value をメトリクス辞書に追加して、MLflowの子ラン作成に使用
        flat_metrics["n_shots_value"] = n_shots_value
        
        for ds, ds_res in results_full.get("results", {}).items():
            details = ds_res.get("details", {})
            for key, value in details.items():
                if key.endswith("_details") or key.endswith("_error_rate"):
                    continue
                
                # データセット名から余分な情報を除去
                original_ds_name = ds.split('/')[-1].replace('.json', '')
                
                # n_shotサフィックスがあれば取り除く（すでに含まれている場合）
                ds_name = original_ds_name
                for shot_suffix in ["_0shot", "_1shot", "_2shot", "_3shot", "_4shot", "_5shot"]:
                    if shot_suffix in ds_name:
                        ds_name = ds_name.replace(shot_suffix, "")
                        break
                
                # シンプルな解決 - 既に正規化されているメトリクスを使用
                # キーにショット情報が含まれているかチェック
                if any('shot' in part for part in key.split('_')):
                    # 既にショット情報が含まれている場合はそのまま使用
                    flat_metrics[key] = value
                else:
                    # ショット情報がない場合は追加
                    normalized_key = f"{ds_name}_{n_shots_value}shot_{key}"
                    flat_metrics[normalized_key] = value
                
                # n_shots_value をメトリクス辞書に保存（MLflowログ用）
                flat_metrics["n_shots_value"] = n_shots_value
        
        # メトリクスが空の場合は警告
        if not flat_metrics:
            logger.warning(f"推論 {inference_id} のメトリクスが空です。評価が正しく行われなかった可能性があります。")
            # メトリクスが空でも完了とするが、エラーメッセージを設定
            inference_repo.update_inference(inference_id, {
                "status": InferenceStatus.COMPLETED,
                "progress": 100,
                "metrics": {},
                "error": "メトリクスの計算に失敗しました。データセットとモデルの組み合わせが適切か確認してください。"
            })
        else:
            # MLflowにメトリクスをログ
            try:
                # ログ用の完全なモデル名を構築（モデル名にはn_shots情報を含めない - 同一モデルの異なるn_shot設定を同じランに記録するため）
                full_model_name = f"{provider_name}/{model_name}"
                n_shots_value = evaluation_request.n_shots[0] if evaluation_request.n_shots and len(evaluation_request.n_shots) > 0 else 0
                logger.info(f"🔄 推論 {inference_id} の評価結果をMLflowに記録します: {full_model_name} (n_shots: {n_shots_value})")
                
                # メトリクスサンプルをログ
                metrics_sample = list(flat_metrics.items())[:5]
                logger.info(f"📊 メトリクスの例 (5件): {metrics_sample}")
                
                # メトリクスデータのログファイルを作成（トラブルシューティング用）
                from app.utils.logging import log_evaluation_results
                import time
                metrics_log_file = f"/app/inference_metrics_{provider_name}_{model_name}{n_shots_suffix}_{int(time.time())}.json"
                with open(metrics_log_file, "w") as f:
                    json.dump({
                        "inference_id": inference_id,
                        "provider": provider_name,
                        "model": model_name,
                        "n_shots": n_shots_value,
                        "n_shots_suffix": n_shots_suffix,
                        "timestamp": datetime.now().isoformat(),
                        "metrics": flat_metrics
                    }, f, indent=2)
                logger.info(f"📊 推論メトリクスデータをログファイルに保存しました: {metrics_log_file}")
                
                # MLflowへのロギング実行（デバッグ詳細付き）
                from app.utils.logging import log_evaluation_results
                
                # メトリクスのタイプを確認（デバッグ用）
                for key, value in flat_metrics.items():
                    logger.info(f"📊 メトリクスの型確認: {key}={value} (type: {type(value).__name__})")
                    
                    # 値が数値でない場合は補正
                    if not isinstance(value, (int, float)):
                        try:
                            flat_metrics[key] = float(value)
                            logger.info(f"🔄 メトリクスを数値型に変換: {key}={flat_metrics[key]}")
                        except (ValueError, TypeError):
                            logger.warning(f"⚠️ メトリクス {key} を数値に変換できません: {value}")
                
                # n_shotsの情報をログ
                logger.info(f"📊 メトリクス名に追加されたn_shots情報: {n_shots_suffix}")
                
                # MLflowにログ記録
                logging_result = await log_evaluation_results(
                    model_name=full_model_name,
                    metrics=flat_metrics
                )
                
                logger.info(f"✅ MLflowへのログ記録結果: {logging_result}")
                
            except Exception as mlflow_error:
                error_message = str(mlflow_error)
                logger.error(f"❌ MLflowへのログ記録中にエラーが発生: {error_message}", exc_info=True)
                
                # エラーをファイルに記録
                import traceback
                error_log_file = f"/app/inference_mlflow_error_{provider_name}_{model_name}_{int(time.time())}.txt"
                with open(error_log_file, "w") as f:
                    f.write(f"Error logging metrics for inference {inference_id} ({provider_name}/{model_name}): {error_message}\n\n")
                    traceback.print_exc(file=f)
                logger.error(f"❌ MLflowエラーログをファイルに保存しました: {error_log_file}")
            
            # 推論のステータスを完了に更新（メトリクスあり）
            inference_repo.update_inference(inference_id, {
                "status": InferenceStatus.COMPLETED,
                "progress": 100,
                "metrics": flat_metrics,
                "error": None  # エラーフィールドをクリア
            })
        
        logger.info(f"推論 {inference_id} の評価が完了しました")
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"推論 {inference_id} の評価中にエラーが発生しました: {str(e)}", exc_info=True)
        
        # エラーの詳細情報を取得
        error_message = str(e)
        error_type = e.__class__.__name__
        
        # エラー発生場所の特定を試みる
        error_context = ""
        try:
            tb = traceback.extract_tb(e.__traceback__)
            if tb:
                last_frame = tb[-1]
                error_context = f"{last_frame.filename}の{last_frame.name}関数({last_frame.lineno}行目)"
        except:
            pass
        
        # エラー時は推論のステータスを失敗に更新（詳細なエラー情報付き）
        detailed_error = f"エラー: {error_type} - {error_message}"
        if error_context:
            detailed_error += f"\n場所: {error_context}"
        
        inference_repo.update_inference(inference_id, {
            "status": InferenceStatus.FAILED,
            "error": detailed_error
        })


@router.get("/{inference_id}", response_model=Inference)
async def get_inference(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を取得します。
    
    Args:
        inference_id: 推論ID
        
    Returns:
        Inference: 推論情報
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 結果を変換
        results = []
        for res in inference_db.get("results", []):
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            ))
        
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(inference_db["created_at"]) if isinstance(inference_db["created_at"], str) else inference_db["created_at"]
        updated_at = datetime.fromisoformat(inference_db["updated_at"]) if isinstance(inference_db["updated_at"], str) else inference_db["updated_at"]
        completed_at = None
        if inference_db.get("completed_at"):
            completed_at = datetime.fromisoformat(inference_db["completed_at"]) if isinstance(inference_db["completed_at"], str) else inference_db["completed_at"]
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=inference_db["id"],
            name=inference_db["name"],
            description=inference_db.get("description"),
            dataset_id=inference_db["dataset_id"],
            provider_id=inference_db["provider_id"],
            model_id=inference_db["model_id"],
            status=InferenceStatus(inference_db["status"]),
            progress=inference_db["progress"],
            metrics=inference_db.get("metrics"),
            results=results,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error=inference_db.get("error")
        )
        
        return inference
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論取得エラー: {str(e)}"
        )


@router.put("/{inference_id}", response_model=Inference)
async def update_inference(
    inference_data: InferenceUpdate,
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を更新します。
    
    Args:
        inference_id: 更新する推論のID
        inference_data: 更新データ
        
    Returns:
        Inference: 更新された推論情報
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 更新データを準備
        update_data = inference_data.dict(exclude_unset=True)
        
        # 更新を実行
        updated_inference = inference_repo.update_inference(inference_id, update_data)
        
        if not updated_inference:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="推論の更新に失敗しました"
            )
        
        # 結果を変換
        results = []
        for res in updated_inference.get("results", []):
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            ))
        
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(updated_inference["created_at"]) if isinstance(updated_inference["created_at"], str) else updated_inference["created_at"]
        updated_at = datetime.fromisoformat(updated_inference["updated_at"]) if isinstance(updated_inference["updated_at"], str) else updated_inference["updated_at"]
        completed_at = None
        if updated_inference.get("completed_at"):
            completed_at = datetime.fromisoformat(updated_inference["completed_at"]) if isinstance(updated_inference["completed_at"], str) else updated_inference["completed_at"]
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=updated_inference["id"],
            name=updated_inference["name"],
            description=updated_inference.get("description"),
            dataset_id=updated_inference["dataset_id"],
            provider_id=updated_inference["provider_id"],
            model_id=updated_inference["model_id"],
            status=InferenceStatus(updated_inference["status"]),
            progress=updated_inference["progress"],
            metrics=updated_inference.get("metrics"),
            results=results,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error=updated_inference.get("error")
        )
        
        return inference
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論更新エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論更新エラー: {str(e)}"
        )


@router.delete("/{inference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inference(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を削除します。
    
    Args:
        inference_id: 削除する推論のID
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 削除を実行
        success = inference_repo.delete_inference(inference_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="推論の削除に失敗しました"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論削除エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論削除エラー: {str(e)}"
        )


@router.post("/{inference_id}/run", response_model=Inference)
async def run_inference(
    background_tasks: BackgroundTasks,
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論を実行します。
    
    Args:
        inference_id: 実行する推論のID
        background_tasks: バックグラウンドタスク
        
    Returns:
        Inference: 実行結果の推論情報
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 現在のステータスをチェック
        if inference_db["status"] == InferenceStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="推論は既に実行中です"
            )
        
        # プロバイダとモデル情報の取得
        provider_repo = get_provider_repository()
        model_repo = get_model_repository()
        
        provider = provider_repo.get_provider_by_id(inference_db["provider_id"])
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"プロバイダID '{inference_db['provider_id']}' が見つかりません"
            )
        
        model = model_repo.get_model_by_id(inference_db["model_id"])
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"モデルID '{inference_db['model_id']}' が見つかりません"
            )
        
        # パラメータを取得
        parameters = inference_db.get("parameters", {})
        
        # データセット名を抽出
        dataset_name = inference_db["dataset_id"].split('/')[-1].replace('.json', '')
        
        # データセットタイプを取得（パラメータに保存されていれば使用）
        dataset_type = None
        if inference_db.get("parameters") and "dataset_type" in inference_db["parameters"]:
            dataset_type = inference_db["parameters"]["dataset_type"]
            logger.info(f"パラメータからデータセットタイプを取得: {dataset_type}")
        
        # データセットを取得
        from app.utils.dataset.operations import get_dataset_by_name
        dataset_info = None
        
        # データセットタイプが指定されている場合は取得を試みる
        if dataset_type:
            dataset_info = get_dataset_by_name(dataset_name, dataset_type)
            logger.info(f"データセット取得（タイプ指定あり）: {dataset_name}, タイプ: {dataset_type}, 結果: {dataset_info is not None}")
        
        # タイプ指定が無いか取得に失敗した場合は、タイプなしで再試行
        if not dataset_info:
            dataset_info = get_dataset_by_name(dataset_name)
            if dataset_info:
                # 取得できた場合はそのタイプを記録
                dataset_type = dataset_info["metadata"].type
                logger.info(f"データセット取得（タイプ指定なし）: {dataset_name}, 検出タイプ: {dataset_type}")
        
        # それでも取得できない場合はエラー
        if not dataset_info:
            logger.error(f"データセットが見つかりません: {dataset_name}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"データセット '{dataset_name}' が見つかりません"
            )
        
        # モデル設定を構築
        model_config = ModelConfig(
            provider=provider["type"],
            model_name=model["name"],
            max_tokens=parameters.get("max_tokens", 512),
            temperature=parameters.get("temperature", 0.7),
            top_p=parameters.get("top_p", 1.0)
        )
        
        # 評価リクエストを構築
        evaluation_request = EvaluationRequest(
            datasets=[dataset_name],
            num_samples=parameters.get("num_samples", 100),
            n_shots=[parameters.get("n_shots", 0)],
            model=model_config
        )
        
        # 推論のステータスを更新
        inference_repo.update_inference(inference_id, {
            "status": InferenceStatus.PENDING,
            "progress": 0,
            "error": None
        })
        
        # 背景タスクで評価を実行
        background_tasks.add_task(
            execute_inference_evaluation,
            inference_id=inference_id,
            evaluation_request=evaluation_request,
            provider_name=provider["type"],
            model_name=model["name"]
        )
        
        # 更新された推論を取得
        updated_inference = inference_repo.get_inference_by_id(inference_id)
        
        # 結果を変換
        results = []
        for res in updated_inference.get("results", []):
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            ))
        
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(updated_inference["created_at"]) if isinstance(updated_inference["created_at"], str) else updated_inference["created_at"]
        updated_at = datetime.fromisoformat(updated_inference["updated_at"]) if isinstance(updated_inference["updated_at"], str) else updated_inference["updated_at"]
        completed_at = None
        if updated_inference.get("completed_at"):
            completed_at = datetime.fromisoformat(updated_inference["completed_at"]) if isinstance(updated_inference["completed_at"], str) else updated_inference["completed_at"]
        
        # 推論オブジェクトを構築
        inference = Inference(
            id=updated_inference["id"],
            name=updated_inference["name"],
            description=updated_inference.get("description"),
            dataset_id=updated_inference["dataset_id"],
            provider_id=updated_inference["provider_id"],
            model_id=updated_inference["model_id"],
            status=InferenceStatus(updated_inference["status"]),
            progress=updated_inference["progress"],
            metrics=updated_inference.get("metrics"),
            results=results,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error=updated_inference.get("error")
        )
        
        return inference
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論実行エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論実行エラー: {str(e)}"
        )


@router.get("/{inference_id}/results", response_model=List[InferenceResult])
async def get_inference_results(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論の結果一覧を取得します。
    
    Args:
        inference_id: 推論ID
        
    Returns:
        List[InferenceResult]: 推論結果一覧
    """
    try:
        # リポジトリから推論を取得（存在チェック）
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # 推論結果を取得
        results_db = inference_repo.get_inference_results(inference_id)
        
        # API応答モデルにマッピング
        results = []
        for res in results_db:
            # 日付文字列をdatetimeに変換
            created_at = datetime.fromisoformat(res["created_at"]) if isinstance(res["created_at"], str) else res["created_at"]
            
            results.append(InferenceResult(
                id=res["id"],
                inference_id=res["inference_id"],
                input=res["input"],
                expected_output=res.get("expected_output"),
                actual_output=res["actual_output"],
                metrics=res.get("metrics"),
                latency=res.get("latency"),
                token_count=res.get("token_count"),
                created_at=created_at
            ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論結果取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論結果取得エラー: {str(e)}"
        )
        

@router.get("/{inference_id}/detail", response_model=dict)
async def get_inference_detail(
    inference_id: str = Path(..., description="推論ID")
):
    """
    特定の推論の詳細情報を取得します。
    
    Args:
        inference_id: 推論ID
        
    Returns:
        dict: 推論の詳細情報（基本情報、データセット情報、評価結果などを含む）
    """
    try:
        # リポジトリから推論を取得
        inference_repo = get_inference_repository()
        inference_db = inference_repo.get_inference_by_id(inference_id)
        
        if not inference_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"推論ID '{inference_id}' が見つかりません"
            )
        
        # プロバイダとモデル情報の取得
        provider_repo = get_provider_repository()
        model_repo = get_model_repository()
        
        provider = provider_repo.get_provider_by_id(inference_db["provider_id"])
        model = model_repo.get_model_by_id(inference_db["model_id"])
        
        # 結果のサンプルを取得（最大10件）
        results_db = inference_repo.get_inference_results(inference_id, limit=10)
        
        # 結果をAPI応答形式に変換
        results = []
        for res in results_db:
            results.append({
                "id": res["id"],
                "input": res["input"],
                "expected_output": res.get("expected_output"),
                "actual_output": res["actual_output"],
                "metrics": res.get("metrics"),
                "latency": res.get("latency"),
                "token_count": res.get("token_count")
            })
            
        # 保存されたJSONファイルの取得を試みる
        import os
        inference_json_path = f"/app/results/{inference_id}/inference.json"
        results_json_data = None
        saved_results_path = None
        
        if os.path.exists(inference_json_path):
            try:
                with open(inference_json_path, "r", encoding="utf-8") as f:
                    inference_info = json.load(f)
                    saved_results_path = inference_info.get("results_file")
                    
                if saved_results_path and os.path.exists(saved_results_path):
                    with open(saved_results_path, "r", encoding="utf-8") as f:
                        results_json_data = json.load(f)
                        logger.info(f"保存されたJSON結果ファイルを読み込みました: {saved_results_path}")
            except Exception as e:
                logger.error(f"JSON結果ファイルの読み込みエラー: {str(e)}", exc_info=True)
        
        # パラメータ情報
        parameters = inference_db.get("parameters", {})
        
        # 推論結果に関する追加統計を計算
        results_summary = {
            "processed_items": len(inference_db.get("results", [])),
            "sample_results": results
        }
        
        # 成功数とエラー数をカウント
        success_count = 0
        error_count = 0
        total_latency = 0
        total_tokens = 0
        
        for result in inference_db.get("results", []):
            if result.get("error"):
                error_count += 1
            else:
                success_count += 1
                
            if result.get("latency"):
                total_latency += result.get("latency", 0)
                
            if result.get("token_count"):
                total_tokens += result.get("token_count", 0)
        
        # 平均を計算
        results_count = len(inference_db.get("results", []))
        avg_latency = total_latency / results_count if results_count > 0 else 0
        avg_tokens = total_tokens / results_count if results_count > 0 else 0
        
        # サマリーに追加
        results_summary.update({
            "success_count": success_count,
            "error_count": error_count,
            "avg_latency": avg_latency,
            "avg_tokens": avg_tokens
        })
        
        # データセット情報にサンプル数を追加
        dataset_name = inference_db["dataset_id"].split('/')[-1].replace('.json', '')
        
        # 詳細情報の構築
        detail = {
            "basic_info": {
                "id": inference_db["id"],
                "name": inference_db["name"],
                "description": inference_db.get("description"),
                "status": inference_db["status"],
                "progress": inference_db["progress"],
                "created_at": inference_db["created_at"],
                "updated_at": inference_db["updated_at"],
                "completed_at": inference_db.get("completed_at")
            },
            "model_info": {
                "provider_id": inference_db["provider_id"],
                "provider_name": provider["name"] if provider else None,
                "provider_type": provider["type"] if provider else None,
                "model_id": inference_db["model_id"],
                "model_name": model["name"] if model else None,
                "model_display_name": model.get("display_name") if model else None,
                "max_tokens": parameters.get("max_tokens", 512),
                "temperature": parameters.get("temperature", 0.7),
                "top_p": parameters.get("top_p", 1.0)
            },
            "dataset_info": {
                "name": dataset_name,
                "dataset_id": inference_db["dataset_id"],
                "item_count": results_count,
                "sample_count": parameters.get("num_samples", 100),
                "n_shots": parameters.get("n_shots", 0)
            },
            "results_summary": results_summary,
            "evaluation_metrics": inference_db.get("metrics", {})
        }
        
        # JSONファイルから読み込んだ詳細データがあれば追加
        if results_json_data:
            # JSONから詳細な結果を追加
            detail["json_results"] = results_json_data
            
            # 結果からデータセット詳細を抽出
            if "results" in results_json_data:
                dataset_details = {}
                for ds_name, ds_result in results_json_data["results"].items():
                    # データセットの詳細情報（サンプル数など）
                    if "dataset_info" in ds_result:
                        dataset_details[ds_name] = ds_result["dataset_info"]
                    
                    # 詳細な評価結果（メトリクスの詳細など）
                    if "details" in ds_result:
                        # 既存のメトリクスを拡張
                        for metric_name, metric_value in ds_result["details"].items():
                            # _detailsで終わるものだけを追加（詳細データ）
                            if metric_name.endswith("_details") and isinstance(metric_value, dict):
                                if "metrics_details" not in detail:
                                    detail["metrics_details"] = {}
                                detail["metrics_details"][metric_name] = metric_value
                
                if dataset_details:
                    detail["dataset_details"] = dataset_details
        
        # エラー情報があれば追加
        if inference_db.get("error"):
            detail["error"] = inference_db["error"]
            
        # 評価結果のパフォーマンスサマリーを追加（存在する場合）
        if inference_db.get("metrics"):
            metrics = inference_db["metrics"]
            accuracy_metrics = {k: v for k, v in metrics.items() if "accuracy" in k.lower()}
            f1_metrics = {k: v for k, v in metrics.items() if "f1" in k.lower()}
            latency_metrics = {k: v for k, v in metrics.items() if "latency" in k.lower()}
            
            detail["performance_summary"] = {
                "accuracy": accuracy_metrics,
                "f1_score": f1_metrics,
                "latency": latency_metrics,
                "other_metrics": {k: v for k, v in metrics.items() 
                                 if k not in accuracy_metrics and k not in f1_metrics and k not in latency_metrics}
            }
        
        return detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推論詳細取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推論詳細取得エラー: {str(e)}"
        )