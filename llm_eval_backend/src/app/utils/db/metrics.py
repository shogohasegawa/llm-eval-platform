"""
メトリクスリポジトリモジュール

メトリクス情報のCRUD操作を提供します。
"""
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.utils.db import get_db

# ロガーの設定
logger = logging.getLogger(__name__)


class MetricRepository:
    """
    メトリクス情報のCRUD操作を提供するクラス
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        self.db = get_db()
    
    def create_metric(self, metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        メトリクスを作成
        
        Args:
            metric_data: メトリクスデータ
                {
                    "name": str,
                    "type": str,
                    "description": Optional[str],
                    "is_higher_better": bool,
                    "parameters": Optional[Dict[str, Any]]
                }
                
        Returns:
            作成されたメトリクス情報
        """
        metric_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # is_higher_betterをIntに変換
        is_higher_better = 1 if metric_data.get("is_higher_better", True) else 0
        
        # parametersをJSON文字列に変換
        parameters = None
        if metric_data.get("parameters"):
            parameters = json.dumps(metric_data["parameters"])
        
        query = """
        INSERT INTO metrics 
        (id, name, type, description, is_higher_better, parameters, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            metric_id,
            metric_data["name"],
            metric_data["type"],
            metric_data.get("description"),
            is_higher_better,
            parameters,
            now,
            now
        )
        
        try:
            self.db.execute(query, params)
            self.db.commit()
            
            # 作成したメトリクスを取得して返す
            return self.get_metric_by_id(metric_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"メトリクス作成エラー: {e}")
            raise
    
    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """
        すべてのメトリクスを取得
        
        Returns:
            メトリクスのリスト
        """
        query = """
        SELECT id, name, type, description, is_higher_better, parameters, created_at, updated_at
        FROM metrics
        ORDER BY created_at DESC
        """
        
        try:
            metrics = self.db.fetch_all(query)
            
            # 整形処理
            for metric in metrics:
                # is_higher_betterをブール値に変換
                metric["is_higher_better"] = bool(metric["is_higher_better"])
                
                # parametersをJSONから辞書に変換
                if metric["parameters"]:
                    try:
                        metric["parameters"] = json.loads(metric["parameters"])
                    except json.JSONDecodeError:
                        metric["parameters"] = {}
                else:
                    metric["parameters"] = {}
            
            return metrics
        except Exception as e:
            logger.error(f"メトリクス取得エラー: {e}")
            raise
    
    def get_metric_by_id(self, metric_id: str) -> Optional[Dict[str, Any]]:
        """
        IDによりメトリクスを取得
        
        Args:
            metric_id: メトリクスID
            
        Returns:
            メトリクス情報またはNone
        """
        query = """
        SELECT id, name, type, description, is_higher_better, parameters, created_at, updated_at
        FROM metrics
        WHERE id = ?
        """
        
        try:
            metric = self.db.fetch_one(query, (metric_id,))
            
            if metric:
                # is_higher_betterをブール値に変換
                metric["is_higher_better"] = bool(metric["is_higher_better"])
                
                # parametersをJSONから辞書に変換
                if metric["parameters"]:
                    try:
                        metric["parameters"] = json.loads(metric["parameters"])
                    except json.JSONDecodeError:
                        metric["parameters"] = {}
                else:
                    metric["parameters"] = {}
            
            return metric
        except Exception as e:
            logger.error(f"メトリクス取得エラー: {e}")
            raise
    
    def update_metric(self, metric_id: str, metric_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        メトリクスを更新
        
        Args:
            metric_id: 更新するメトリクスのID
            metric_data: 更新データ
                {
                    "name": Optional[str],
                    "type": Optional[str],
                    "description": Optional[str],
                    "is_higher_better": Optional[bool],
                    "parameters": Optional[Dict[str, Any]]
                }
                
        Returns:
            更新されたメトリクス情報またはNone
        """
        # 既存のメトリクスを取得
        metric = self.get_metric_by_id(metric_id)
        if not metric:
            return None
        
        now = datetime.now().isoformat()
        
        # 更新するフィールドを準備
        updates = []
        params = []
        
        # 更新対象のスカラーフィールド
        scalar_fields = ["name", "type", "description", "is_higher_better"]
        
        for field in scalar_fields:
            if field in metric_data and metric_data[field] is not None:
                updates.append(f"{field} = ?")
                
                # is_higher_betterの場合はブール値をIntに変換
                if field == "is_higher_better":
                    params.append(1 if metric_data[field] else 0)
                else:
                    params.append(metric_data[field])
        
        # parametersフィールドの特殊処理
        if "parameters" in metric_data:
            updates.append("parameters = ?")
            params.append(json.dumps(metric_data["parameters"]) if metric_data["parameters"] else None)
        
        # 更新日時は常に更新
        updates.append("updated_at = ?")
        params.append(now)
        
        # メトリクスIDをパラメータに追加
        params.append(metric_id)
        
        if not updates:
            # 更新するフィールドがない場合は現在のメトリクス情報を返す
            return metric
        
        query = f"""
        UPDATE metrics
        SET {', '.join(updates)}
        WHERE id = ?
        """
        
        try:
            self.db.execute(query, tuple(params))
            self.db.commit()
            
            # 更新したメトリクスを取得して返す
            return self.get_metric_by_id(metric_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"メトリクス更新エラー: {e}")
            raise
    
    def delete_metric(self, metric_id: str) -> bool:
        """
        メトリクスを削除
        
        Args:
            metric_id: 削除するメトリクスのID
            
        Returns:
            削除成功の場合はTrue、それ以外はFalse
        """
        query = "DELETE FROM metrics WHERE id = ?"
        
        try:
            cursor = self.db.execute(query, (metric_id,))
            self.db.commit()
            
            # 削除された行数で成功を判定
            return cursor.rowcount > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"メトリクス削除エラー: {e}")
            raise


# シングルトンインスタンスを取得する関数
def get_metric_repository() -> MetricRepository:
    """
    メトリクスリポジトリのインスタンスを取得
    
    Returns:
        MetricRepositoryインスタンス
    """
    return MetricRepository()