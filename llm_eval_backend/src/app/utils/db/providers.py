"""
プロバイダーリポジトリモジュール

プロバイダー情報のCRUD操作を提供します。
"""
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.utils.db import get_db

# ロガーの設定
logger = logging.getLogger(__name__)


class ProviderRepository:
    """
    プロバイダー情報のCRUD操作を提供するクラス
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        self.db = get_db()
    
    def create_provider(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        プロバイダーを作成
        
        Args:
            provider_data: プロバイダーデータ
                {
                    "name": str,
                    "type": str,
                    "endpoint": Optional[str],
                    "api_key": Optional[str],
                    "is_active": bool
                }
                
        Returns:
            作成されたプロバイダー情報
        """
        provider_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # is_activeをIntに変換
        is_active = 1 if provider_data.get("is_active", True) else 0
        
        query = """
        INSERT INTO providers 
        (id, name, type, endpoint, api_key, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            provider_id,
            provider_data["name"],
            provider_data["type"],
            provider_data.get("endpoint"),
            provider_data.get("api_key"),
            is_active,
            now,
            now
        )
        
        try:
            self.db.execute(query, params)
            self.db.commit()
            
            # 作成したプロバイダーを取得して返す
            return self.get_provider_by_id(provider_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"プロバイダー作成エラー: {e}")
            raise
    
    def get_all_providers(self) -> List[Dict[str, Any]]:
        """
        すべてのプロバイダーを取得
        
        Returns:
            プロバイダーのリスト
        """
        query = """
        SELECT id, name, type, endpoint, api_key, is_active, created_at, updated_at
        FROM providers
        ORDER BY created_at DESC
        """
        
        try:
            providers = self.db.fetch_all(query)
            
            # is_activeをブール値に変換
            for provider in providers:
                provider["is_active"] = bool(provider["is_active"])
            
            return providers
        except Exception as e:
            logger.error(f"プロバイダー取得エラー: {e}")
            raise
    
    def get_provider_by_id(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        IDによりプロバイダーを取得

        Args:
            provider_id: プロバイダーID

        Returns:
            プロバイダー情報またはNone
        """
        query = """
        SELECT id, name, type, endpoint, api_key, is_active, created_at, updated_at
        FROM providers
        WHERE id = ?
        """

        try:
            provider = self.db.fetch_one(query, (provider_id,))

            if provider:
                # is_activeをブール値に変換
                provider["is_active"] = bool(provider["is_active"])

            return provider
        except Exception as e:
            logger.error(f"プロバイダー取得エラー: {e}")
            raise

    def get_provider_by_name(self, name_or_type: str) -> Optional[Dict[str, Any]]:
        """
        名前またはタイプによりプロバイダーを取得

        Args:
            name_or_type: プロバイダー名またはタイプ（例: "openai", "anthropic"など）

        Returns:
            プロバイダー情報またはNone
        """
        query = """
        SELECT id, name, type, endpoint, api_key, is_active, created_at, updated_at
        FROM providers
        WHERE name = ? OR type = ?
        LIMIT 1
        """

        try:
            provider = self.db.fetch_one(query, (name_or_type, name_or_type))

            if provider:
                # is_activeをブール値に変換
                provider["is_active"] = bool(provider["is_active"])

            return provider
        except Exception as e:
            logger.error(f"プロバイダー取得エラー: {e}")
            raise
    
    def update_provider(self, provider_id: str, provider_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        プロバイダーを更新
        
        Args:
            provider_id: 更新するプロバイダーのID
            provider_data: 更新データ
                {
                    "name": Optional[str],
                    "type": Optional[str],
                    "endpoint": Optional[str],
                    "api_key": Optional[str],
                    "is_active": Optional[bool]
                }
                
        Returns:
            更新されたプロバイダー情報またはNone
        """
        # 既存のプロバイダーを取得
        provider = self.get_provider_by_id(provider_id)
        if not provider:
            return None
        
        now = datetime.now().isoformat()
        
        # 更新するフィールドを準備
        updates = []
        params = []
        
        # 更新対象フィールド
        fields = ["name", "type", "endpoint", "api_key", "is_active"]
        
        for field in fields:
            if field in provider_data:
                updates.append(f"{field} = ?")
                
                # is_activeの場合はブール値をIntに変換
                if field == "is_active" and provider_data[field] is not None:
                    params.append(1 if provider_data[field] else 0)
                else:
                    params.append(provider_data[field])
        
        # 更新日時は常に更新
        updates.append("updated_at = ?")
        params.append(now)
        
        # プロバイダーIDをパラメータに追加
        params.append(provider_id)
        
        query = f"""
        UPDATE providers
        SET {', '.join(updates)}
        WHERE id = ?
        """
        
        try:
            self.db.execute(query, tuple(params))
            self.db.commit()
            
            # 更新したプロバイダーを取得して返す
            return self.get_provider_by_id(provider_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"プロバイダー更新エラー: {e}")
            raise
    
    def delete_provider(self, provider_id: str) -> bool:
        """
        プロバイダーを削除
        
        Args:
            provider_id: 削除するプロバイダーのID
            
        Returns:
            削除成功の場合はTrue、それ以外はFalse
        """
        query = "DELETE FROM providers WHERE id = ?"
        
        try:
            cursor = self.db.execute(query, (provider_id,))
            self.db.commit()
            
            # 削除された行数で成功を判定
            return cursor.rowcount > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"プロバイダー削除エラー: {e}")
            raise


# APIキーを取得する関数
def get_api_key_by_provider_name(provider_name: str) -> Optional[str]:
    """
    プロバイダー名またはタイプからAPIキーを取得する

    Args:
        provider_name: プロバイダー名またはタイプ（例: "openai", "anthropic"など）

    Returns:
        APIキー、見つからない場合はNone
    """
    try:
        # プロバイダーリポジトリを取得
        provider_repo = get_provider_repository()

        # 名前またはタイプでプロバイダーを検索
        provider = provider_repo.get_provider_by_name(provider_name)

        if provider and provider.get("api_key"):
            logger.info(f"プロバイダー '{provider_name}' のAPIキーを取得しました")
            return provider["api_key"]

        # プロバイダーが見つからない、またはAPIキーが設定されていない場合
        logger.warning(f"プロバイダー '{provider_name}' のAPIキーが見つかりません")
        return None
    except Exception as e:
        logger.error(f"APIキー取得エラー: {e}")
        return None

# シングルトンインスタンスを取得する関数
def get_provider_repository() -> ProviderRepository:
    """
    プロバイダーリポジトリのインスタンスを取得

    Returns:
        ProviderRepositoryインスタンス
    """
    return ProviderRepository()
