"""
推論リポジトリモジュール

推論データのCRUD操作を提供します。
"""
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.utils.db import get_db
from app.utils.db.models import get_model_repository
from app.utils.db.providers import get_provider_repository
from app.api.models import InferenceStatus
from app.utils.datetime_helper import get_current_time_str, parse_datetime

# ロガーの設定
logger = logging.getLogger(__name__)


class InferenceRepository:
    """
    推論データのCRUD操作を提供するクラス
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        self.db = get_db()
        self.model_repo = get_model_repository()
        self.provider_repo = get_provider_repository()
    
    def create_inference(self, inference_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        推論を作成
        
        Args:
            inference_data: 推論データ
                {
                    "name": str,
                    "description": Optional[str],
                    "dataset_id": str,
                    "provider_id": str,
                    "model_id": str,
                    "status": str,  # "pending", "running", "completed", "failed"
                    "progress": int,  # 0-100
                    "metrics": Optional[Dict[str, float]],
                    "parameters": Optional[Dict[str, Any]]  # max_tokens, temperature, top_p, num_samples など
                }
                
        Returns:
            作成された推論情報
        """
        # プロバイダーとモデルが存在するか確認
        provider = self.provider_repo.get_provider_by_id(inference_data["provider_id"])
        if not provider:
            raise ValueError(f"プロバイダーID '{inference_data['provider_id']}' が存在しません")
        
        model = self.model_repo.get_model_by_id(inference_data["model_id"])
        if not model:
            raise ValueError(f"モデルID '{inference_data['model_id']}' が存在しません")
        
        inference_id = str(uuid.uuid4())
        now = get_current_time_str()  # JSTタイムゾーンを使用
        
        # metricsとparametersをJSON文字列に変換
        metrics = None
        if inference_data.get("metrics"):
            metrics = json.dumps(inference_data["metrics"])
        
        parameters = None
        if inference_data.get("parameters"):
            parameters = json.dumps(inference_data["parameters"])
        
        # statusがなければpendingをデフォルトとする
        status = inference_data.get("status", InferenceStatus.PENDING)
        
        # progressがなければ0をデフォルトとする
        progress = inference_data.get("progress", 0)
        
        query = """
        INSERT INTO inferences 
        (id, name, description, dataset_id, provider_id, model_id, status, progress, metrics, parameters, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            inference_id,
            inference_data["name"],
            inference_data.get("description"),
            inference_data["dataset_id"],
            inference_data["provider_id"],
            inference_data["model_id"],
            status,
            progress,
            metrics,
            parameters,
            now,
            now
        )
        
        try:
            self.db.execute(query, params)
            self.db.commit()
            
            # 作成した推論を取得して返す
            return self.get_inference_by_id(inference_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"推論作成エラー: {e}")
            raise
    
    def get_all_inferences(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        すべての推論を取得
        
        Args:
            filters: フィルター条件
                {
                    "dataset_id": Optional[str],
                    "provider_id": Optional[str],
                    "model_id": Optional[str],
                    "status": Optional[str]
                }
        
        Returns:
            推論のリスト
        """
        query = """
        SELECT i.id, i.name, i.description, i.dataset_id, i.provider_id, i.model_id, 
               i.status, i.progress, i.metrics, i.parameters, i.created_at, i.updated_at, 
               i.completed_at, i.error
        FROM inferences i
        """
        
        # フィルター条件の適用
        where_clauses = []
        params = []
        
        if filters:
            if filters.get("dataset_id"):
                where_clauses.append("i.dataset_id = ?")
                params.append(filters["dataset_id"])
            
            if filters.get("provider_id"):
                where_clauses.append("i.provider_id = ?")
                params.append(filters["provider_id"])
            
            if filters.get("model_id"):
                where_clauses.append("i.model_id = ?")
                params.append(filters["model_id"])
            
            if filters.get("status"):
                where_clauses.append("i.status = ?")
                params.append(filters["status"])
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY i.created_at DESC"
        
        try:
            inferences = self.db.fetch_all(query, tuple(params))
            
            # 整形処理
            results = []
            for inference in inferences:
                # metricsをJSONから辞書に変換
                if inference["metrics"]:
                    try:
                        inference["metrics"] = json.loads(inference["metrics"])
                    except json.JSONDecodeError:
                        inference["metrics"] = {}
                
                # parametersをJSONから辞書に変換
                if inference["parameters"]:
                    try:
                        inference["parameters"] = json.loads(inference["parameters"])
                    except json.JSONDecodeError:
                        inference["parameters"] = {}
                
                # 推論結果を取得
                inference["results"] = self.get_inference_results(inference["id"])
                
                results.append(inference)
            
            return results
        except Exception as e:
            logger.error(f"推論取得エラー: {e}")
            raise
    
    def get_inference_by_id(self, inference_id: str) -> Optional[Dict[str, Any]]:
        """
        IDにより推論を取得
        
        Args:
            inference_id: 推論ID
            
        Returns:
            推論情報またはNone
        """
        query = """
        SELECT i.id, i.name, i.description, i.dataset_id, i.provider_id, i.model_id, 
               i.status, i.progress, i.metrics, i.parameters, i.created_at, i.updated_at, 
               i.completed_at, i.error
        FROM inferences i
        WHERE i.id = ?
        """
        
        try:
            inference = self.db.fetch_one(query, (inference_id,))
            
            if inference:
                # metricsをJSONから辞書に変換
                if inference["metrics"]:
                    try:
                        inference["metrics"] = json.loads(inference["metrics"])
                    except json.JSONDecodeError:
                        inference["metrics"] = {}
                
                # parametersをJSONから辞書に変換
                if inference["parameters"]:
                    try:
                        inference["parameters"] = json.loads(inference["parameters"])
                    except json.JSONDecodeError:
                        inference["parameters"] = {}
                
                # 推論結果を取得
                inference["results"] = self.get_inference_results(inference_id)
            
            return inference
        except Exception as e:
            logger.error(f"推論取得エラー: {e}")
            raise
    
    def update_inference(self, inference_id: str, inference_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        推論を更新
        
        Args:
            inference_id: 更新する推論のID
            inference_data: 更新データ
                {
                    "name": Optional[str],
                    "description": Optional[str],
                    "status": Optional[str],
                    "progress": Optional[int],
                    "metrics": Optional[Dict[str, float]],
                    "error": Optional[str]
                }
                
        Returns:
            更新された推論情報またはNone
        """
        # 既存の推論を取得
        inference = self.get_inference_by_id(inference_id)
        if not inference:
            return None
        
        now = get_current_time_str()  # JSTタイムゾーンを使用
        
        # 更新するフィールドを準備
        updates = []
        params = []
        
        # 更新対象のスカラーフィールド
        scalar_fields = ["name", "description", "status", "progress", "error"]
        
        for field in scalar_fields:
            if field in inference_data:
                updates.append(f"{field} = ?")
                params.append(inference_data[field])
        
        # 特殊処理: status が 'completed' になった場合は completed_at を設定
        if inference_data.get("status") == InferenceStatus.COMPLETED and (
            inference["status"] != InferenceStatus.COMPLETED or not inference["completed_at"]
        ):
            updates.append("completed_at = ?")
            params.append(now)
        
        # metricsフィールドの特殊処理
        if "metrics" in inference_data:
            updates.append("metrics = ?")
            params.append(json.dumps(inference_data["metrics"]) if inference_data["metrics"] else None)
        
        # 更新日時は常に更新
        updates.append("updated_at = ?")
        params.append(now)
        
        # 推論IDをパラメータに追加
        params.append(inference_id)
        
        query = f"""
        UPDATE inferences
        SET {', '.join(updates)}
        WHERE id = ?
        """
        
        try:
            self.db.execute(query, tuple(params))
            self.db.commit()
            
            # 更新した推論を取得して返す
            return self.get_inference_by_id(inference_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"推論更新エラー: {e}")
            raise
    
    def delete_inference(self, inference_id: str) -> bool:
        """
        推論を削除
        
        Args:
            inference_id: 削除する推論のID
            
        Returns:
            削除成功の場合はTrue、それ以外はFalse
        """
        # 最初に関連する推論結果を削除（CASCADE制約があるので不要だが念のため）
        self.delete_inference_results(inference_id)
        
        query = "DELETE FROM inferences WHERE id = ?"
        
        try:
            cursor = self.db.execute(query, (inference_id,))
            self.db.commit()
            
            # 削除された行数で成功を判定
            return cursor.rowcount > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"推論削除エラー: {e}")
            raise
    
    def create_inference_result(self, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        推論結果を作成
        
        Args:
            result_data: 推論結果データ
                {
                    "inference_id": str,
                    "input": str,
                    "expected_output": Optional[str],
                    "actual_output": str,
                    "metrics": Optional[Dict[str, float]],
                    "latency": Optional[float],
                    "token_count": Optional[int]
                }
                
        Returns:
            作成された推論結果情報
        """
        # 推論が存在するか確認
        inference = self.get_inference_by_id(result_data["inference_id"])
        if not inference:
            raise ValueError(f"推論ID '{result_data['inference_id']}' が存在しません")
        
        result_id = str(uuid.uuid4())
        now = get_current_time_str()  # JSTタイムゾーンを使用
        
        # metricsをJSON文字列に変換
        metrics = None
        if result_data.get("metrics"):
            metrics = json.dumps(result_data["metrics"])
        
        query = """
        INSERT INTO inference_results 
        (id, inference_id, input, expected_output, actual_output, metrics, latency, token_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            result_id,
            result_data["inference_id"],
            result_data["input"],
            result_data.get("expected_output"),
            result_data["actual_output"],
            metrics,
            result_data.get("latency"),
            result_data.get("token_count"),
            now
        )
        
        try:
            self.db.execute(query, params)
            self.db.commit()
            
            # 作成した推論結果を取得して返す
            return self.get_inference_result(result_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"推論結果作成エラー: {e}")
            raise
    
    def get_inference_results(self, inference_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        特定の推論に関連する結果一覧を取得
        
        Args:
            inference_id: 推論ID
            limit: 取得する結果の最大数（指定がない場合はすべての結果を取得）
            
        Returns:
            推論結果のリスト
        """
        query = """
        SELECT id, inference_id, input, expected_output, actual_output, metrics, latency, token_count, created_at
        FROM inference_results
        WHERE inference_id = ?
        ORDER BY created_at ASC
        """
        
        # limitが指定されている場合はクエリに追加
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        
        try:
            results = self.db.fetch_all(query, (inference_id,))
            
            # 整形処理
            for result in results:
                # metricsをJSONから辞書に変換
                if result["metrics"]:
                    try:
                        result["metrics"] = json.loads(result["metrics"])
                    except json.JSONDecodeError:
                        result["metrics"] = {}
            
            return results
        except Exception as e:
            logger.error(f"推論結果取得エラー: {e}")
            raise
    
    def get_inference_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """
        特定の推論結果を取得
        
        Args:
            result_id: 推論結果ID
            
        Returns:
            推論結果情報またはNone
        """
        query = """
        SELECT id, inference_id, input, expected_output, actual_output, metrics, latency, token_count, created_at
        FROM inference_results
        WHERE id = ?
        """
        
        try:
            result = self.db.fetch_one(query, (result_id,))
            
            if result:
                # metricsをJSONから辞書に変換
                if result["metrics"]:
                    try:
                        result["metrics"] = json.loads(result["metrics"])
                    except json.JSONDecodeError:
                        result["metrics"] = {}
            
            return result
        except Exception as e:
            logger.error(f"推論結果取得エラー: {e}")
            raise
    
    def delete_inference_results(self, inference_id: str) -> bool:
        """
        特定の推論に関連する結果をすべて削除
        
        Args:
            inference_id: 削除する推論結果に関連する推論ID
            
        Returns:
            削除成功の場合はTrue、それ以外はFalse
        """
        query = "DELETE FROM inference_results WHERE inference_id = ?"
        
        try:
            cursor = self.db.execute(query, (inference_id,))
            self.db.commit()
            
            # 削除が実行されたら成功と見なす
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"推論結果削除エラー: {e}")
            raise


# シングルトンインスタンスを取得する関数
def get_inference_repository() -> InferenceRepository:
    """
    推論リポジトリのインスタンスを取得
    
    Returns:
        InferenceRepositoryインスタンス
    """
    return InferenceRepository()