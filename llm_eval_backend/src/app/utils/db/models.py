"""
モデルリポジトリモジュール

モデル情報のCRUD操作を提供します。
"""
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.utils.db import get_db
from app.utils.db.providers import get_provider_repository

# ロガーの設定
logger = logging.getLogger(__name__)


class ModelRepository:
    """
    モデル情報のCRUD操作を提供するクラス
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        self.db = get_db()
        self.provider_repo = get_provider_repository()
    
    def create_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        モデルを作成
        
        Args:
            model_data: モデルデータ
                {
                    "provider_id": str,
                    "name": str,
                    "display_name": Optional[str],
                    "description": Optional[str],
                    "parameters": Optional[Dict[str, Any]],
                    "is_active": bool
                }
                
        Returns:
            作成されたモデル情報
        """
        # プロバイダーが存在するか確認
        provider = self.provider_repo.get_provider_by_id(model_data["provider_id"])
        if not provider:
            raise ValueError(f"プロバイダーID '{model_data['provider_id']}' が存在しません")
        
        model_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # display_nameが指定されていない場合はnameを使用
        display_name = model_data.get("display_name") or model_data["name"]
        
        # プロバイダーのエンドポイントとAPIキーを取得
        endpoint = model_data.get("endpoint") or provider.get("endpoint")
        api_key = model_data.get("api_key") or provider.get("api_key")
        
        # is_activeをIntに変換
        is_active = 1 if model_data.get("is_active", True) else 0
        
        # parametersをJSON文字列に変換
        parameters = None
        if model_data.get("parameters"):
            parameters = json.dumps(model_data["parameters"])
        
        query = """
        INSERT INTO models 
        (id, provider_id, name, display_name, description, endpoint, api_key, parameters, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            model_id,
            model_data["provider_id"],
            model_data["name"],
            display_name,
            model_data.get("description"),
            endpoint,
            api_key,
            parameters,
            is_active,
            now,
            now
        )
        
        try:
            self.db.execute(query, params)
            self.db.commit()
            
            # 作成したモデルを取得して返す
            return self.get_model_by_id(model_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"モデル作成エラー: {e}")
            raise
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """
        すべてのモデルを取得
        
        Returns:
            モデルのリスト
        """
        query = """
        SELECT m.id, m.provider_id, m.name, m.display_name, m.description, 
               m.endpoint, m.api_key, m.parameters, m.is_active, 
               m.created_at, m.updated_at, p.name as provider_name
        FROM models m
        JOIN providers p ON m.provider_id = p.id
        ORDER BY m.created_at DESC
        """
        
        try:
            models = self.db.fetch_all(query)
            
            # 整形処理
            for model in models:
                # is_activeをブール値に変換
                model["is_active"] = bool(model["is_active"])
                
                # parametersをJSONから辞書に変換
                if model["parameters"]:
                    try:
                        model["parameters"] = json.loads(model["parameters"])
                    except json.JSONDecodeError:
                        model["parameters"] = {}
            
            return models
        except Exception as e:
            logger.error(f"モデル取得エラー: {e}")
            raise
    
    def get_models_by_provider(self, provider_id: str) -> List[Dict[str, Any]]:
        """
        特定のプロバイダーに属するモデルを取得
        
        Args:
            provider_id: プロバイダーID
            
        Returns:
            モデルのリスト
        """
        query = """
        SELECT m.id, m.provider_id, m.name, m.display_name, m.description, 
               m.endpoint, m.api_key, m.parameters, m.is_active, 
               m.created_at, m.updated_at, p.name as provider_name
        FROM models m
        JOIN providers p ON m.provider_id = p.id
        WHERE m.provider_id = ?
        ORDER BY m.created_at DESC
        """
        
        try:
            models = self.db.fetch_all(query, (provider_id,))
            
            # 整形処理
            for model in models:
                # is_activeをブール値に変換
                model["is_active"] = bool(model["is_active"])
                
                # parametersをJSONから辞書に変換
                if model["parameters"]:
                    try:
                        model["parameters"] = json.loads(model["parameters"])
                    except json.JSONDecodeError:
                        model["parameters"] = {}
            
            return models
        except Exception as e:
            logger.error(f"モデル取得エラー: {e}")
            raise
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        IDによりモデルを取得
        
        Args:
            model_id: モデルID
            
        Returns:
            モデル情報またはNone
        """
        query = """
        SELECT m.id, m.provider_id, m.name, m.display_name, m.description, 
               m.endpoint, m.api_key, m.parameters, m.is_active, 
               m.created_at, m.updated_at, p.name as provider_name
        FROM models m
        JOIN providers p ON m.provider_id = p.id
        WHERE m.id = ?
        """
        
        try:
            model = self.db.fetch_one(query, (model_id,))
            
            if model:
                # is_activeをブール値に変換
                model["is_active"] = bool(model["is_active"])
                
                # parametersをJSONから辞書に変換
                if model["parameters"]:
                    try:
                        model["parameters"] = json.loads(model["parameters"])
                    except json.JSONDecodeError:
                        model["parameters"] = {}
            
            return model
        except Exception as e:
            logger.error(f"モデル取得エラー: {e}")
            raise
    
    def update_model(self, model_id: str, model_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        モデルを更新
        
        Args:
            model_id: 更新するモデルのID
            model_data: 更新データ
                {
                    "provider_id": Optional[str],
                    "name": Optional[str],
                    "display_name": Optional[str],
                    "description": Optional[str],
                    "endpoint": Optional[str],
                    "api_key": Optional[str],
                    "parameters": Optional[Dict[str, Any]],
                    "is_active": Optional[bool]
                }
                
        Returns:
            更新されたモデル情報またはNone
        """
        # 既存のモデルを取得
        model = self.get_model_by_id(model_id)
        if not model:
            return None
        
        # プロバイダーを変更する場合は存在チェック
        if "provider_id" in model_data and model_data["provider_id"] != model["provider_id"]:
            provider = self.provider_repo.get_provider_by_id(model_data["provider_id"])
            if not provider:
                raise ValueError(f"プロバイダーID '{model_data['provider_id']}' が存在しません")
        
        now = datetime.now().isoformat()
        
        # 更新するフィールドを準備
        updates = []
        params = []
        
        # 更新対象のスカラーフィールド
        scalar_fields = ["provider_id", "name", "display_name", "description", "endpoint", "api_key", "is_active"]
        
        for field in scalar_fields:
            if field in model_data:
                updates.append(f"{field} = ?")
                
                # is_activeの場合はブール値をIntに変換
                if field == "is_active" and model_data[field] is not None:
                    params.append(1 if model_data[field] else 0)
                else:
                    params.append(model_data[field])
        
        # parametersフィールドの特殊処理
        if "parameters" in model_data:
            updates.append("parameters = ?")
            params.append(json.dumps(model_data["parameters"]) if model_data["parameters"] else None)
        
        # 更新日時は常に更新
        updates.append("updated_at = ?")
        params.append(now)
        
        # モデルIDをパラメータに追加
        params.append(model_id)
        
        query = f"""
        UPDATE models
        SET {', '.join(updates)}
        WHERE id = ?
        """
        
        try:
            self.db.execute(query, tuple(params))
            self.db.commit()
            
            # 更新したモデルを取得して返す
            return self.get_model_by_id(model_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"モデル更新エラー: {e}")
            raise
    
    def delete_model(self, model_id: str) -> bool:
        """
        モデルを削除
        
        Args:
            model_id: 削除するモデルのID
            
        Returns:
            削除成功の場合はTrue、それ以外はFalse
        """
        query = "DELETE FROM models WHERE id = ?"
        
        try:
            cursor = self.db.execute(query, (model_id,))
            self.db.commit()
            
            # 削除された行数で成功を判定
            return cursor.rowcount > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"モデル削除エラー: {e}")
            raise


# シングルトンインスタンスを取得する関数
def get_model_repository() -> ModelRepository:
    """
    モデルリポジトリのインスタンスを取得
    
    Returns:
        ModelRepositoryインスタンス
    """
    return ModelRepository()
