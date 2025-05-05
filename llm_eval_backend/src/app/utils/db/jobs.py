"""
ジョブリポジトリモジュール

評価ジョブのCRUD操作を提供します。
"""
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.utils.db import get_db
from app.api.models import JobStatus, JobLogLevel, EvaluationRequest

# ロガーの設定
logger = logging.getLogger(__name__)


class JobRepository:
    """
    評価ジョブ情報のCRUD操作を提供するクラス
    """
    
    def __init__(self):
        """リポジトリの初期化"""
        self.db = get_db()
    
    def create_job(self, request_data: EvaluationRequest) -> Dict[str, Any]:
        """
        評価ジョブを作成
        
        Args:
            request_data: 評価リクエストデータ
                
        Returns:
            作成されたジョブ情報
        """
        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # リクエストデータをJSON文字列に変換
        request_json = json.dumps(request_data.dict())
        
        query = """
        INSERT INTO evaluation_jobs 
        (id, status, request_data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """
        
        params = (
            job_id,
            JobStatus.PENDING.value,
            request_json,
            now,
            now
        )
        
        try:
            self.db.execute(query, params)
            self.db.commit()
            
            # 作成したジョブを取得して返す
            return self.get_job_by_id(job_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"ジョブ作成エラー: {e}")
            raise
    
    def get_all_jobs(self, page: int = 1, page_size: int = 10) -> Tuple[List[Dict[str, Any]], int]:
        """
        すべてのジョブを取得
        
        Args:
            page: ページ番号
            page_size: 1ページあたりの件数
            
        Returns:
            (ジョブのリスト, 総件数)のタプル
        """
        count_query = "SELECT COUNT(*) as total FROM evaluation_jobs"
        
        offset = (page - 1) * page_size
        
        query = """
        SELECT id, status, request_data, result_data, error_message, 
               created_at, updated_at, completed_at
        FROM evaluation_jobs
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """
        
        try:
            # 総件数を取得
            total_result = self.db.fetch_one(count_query)
            total = total_result["total"] if total_result else 0
            
            # ジョブを取得
            jobs = self.db.fetch_all(query, (page_size, offset))
            
            # 整形処理
            for job in jobs:
                # リクエストデータをJSONから辞書に変換
                if job["request_data"]:
                    try:
                        job["request_data"] = json.loads(job["request_data"])
                    except json.JSONDecodeError:
                        job["request_data"] = {}
                
                # 結果データをJSONから辞書に変換
                if job["result_data"]:
                    try:
                        job["result_data"] = json.loads(job["result_data"])
                    except json.JSONDecodeError:
                        job["result_data"] = {}
            
            return jobs, total
        except Exception as e:
            logger.error(f"ジョブ取得エラー: {e}")
            raise
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        IDによりジョブを取得
        
        Args:
            job_id: ジョブID
            
        Returns:
            ジョブ情報またはNone
        """
        query = """
        SELECT id, status, request_data, result_data, error_message, 
               created_at, updated_at, completed_at
        FROM evaluation_jobs
        WHERE id = ?
        """
        
        try:
            job = self.db.fetch_one(query, (job_id,))
            
            if job:
                # リクエストデータをJSONから辞書に変換
                if job["request_data"]:
                    try:
                        job["request_data"] = json.loads(job["request_data"])
                    except json.JSONDecodeError:
                        job["request_data"] = {}
                
                # 結果データをJSONから辞書に変換
                if job["result_data"]:
                    try:
                        job["result_data"] = json.loads(job["result_data"])
                    except json.JSONDecodeError:
                        job["result_data"] = {}
            
            return job
        except Exception as e:
            logger.error(f"ジョブ取得エラー: {e}")
            raise
    
    def update_job_status(self, job_id: str, status: JobStatus, 
                        result_data: Optional[Dict[str, Any]] = None,
                        error_message: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        ジョブのステータスを更新
        
        Args:
            job_id: 更新するジョブのID
            status: 新しいステータス
            result_data: 結果データ（完了時のみ）
            error_message: エラーメッセージ（失敗時のみ）
                
        Returns:
            更新されたジョブ情報またはNone
        """
        # 既存のジョブを取得
        job = self.get_job_by_id(job_id)
        if not job:
            return None
        
        now = datetime.now().isoformat()
        
        # 更新するフィールドを準備
        updates = ["status = ?", "updated_at = ?"]
        params = [status.value, now]
        
        # 結果データが提供された場合
        if result_data is not None:
            updates.append("result_data = ?")
            params.append(json.dumps(result_data))
        
        # エラーメッセージが提供された場合
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        # 完了または失敗の場合、完了時刻を設定
        if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            updates.append("completed_at = ?")
            params.append(now)
        
        # IDをパラメータに追加
        params.append(job_id)
        
        query = f"""
        UPDATE evaluation_jobs
        SET {', '.join(updates)}
        WHERE id = ?
        """
        
        try:
            self.db.execute(query, tuple(params))
            self.db.commit()
            
            # 更新したジョブを取得して返す
            return self.get_job_by_id(job_id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"ジョブ更新エラー: {e}")
            raise
    
    def delete_job(self, job_id: str) -> bool:
        """
        ジョブを削除
        
        Args:
            job_id: 削除するジョブのID
            
        Returns:
            削除成功の場合はTrue、それ以外はFalse
        """
        query = "DELETE FROM evaluation_jobs WHERE id = ?"
        
        try:
            cursor = self.db.execute(query, (job_id,))
            self.db.commit()
            
            # 削除された行数で成功を判定
            return cursor.rowcount > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"ジョブ削除エラー: {e}")
            raise
    
    def add_job_log(self, job_id: str, log_level: JobLogLevel, message: str) -> Dict[str, Any]:
        """
        ジョブのログエントリを追加
        
        Args:
            job_id: ジョブID
            log_level: ログレベル
            message: ログメッセージ
            
        Returns:
            作成されたログエントリ情報
        """
        log_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        query = """
        INSERT INTO job_logs 
        (id, job_id, log_level, message, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """
        
        params = (
            log_id,
            job_id,
            log_level.value,
            message,
            now
        )
        
        try:
            self.db.execute(query, params)
            self.db.commit()
            
            return {
                "id": log_id,
                "job_id": job_id,
                "log_level": log_level.value,
                "message": message,
                "timestamp": now
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"ジョブログ追加エラー: {e}")
            raise
    
    def get_job_logs(self, job_id: str) -> List[Dict[str, Any]]:
        """
        特定ジョブのログエントリを取得
        
        Args:
            job_id: ジョブID
            
        Returns:
            ログエントリのリスト
        """
        query = """
        SELECT id, job_id, log_level, message, timestamp
        FROM job_logs
        WHERE job_id = ?
        ORDER BY timestamp ASC
        """
        
        try:
            logs = self.db.fetch_all(query, (job_id,))
            return logs
        except Exception as e:
            logger.error(f"ジョブログ取得エラー: {e}")
            raise


# シングルトンインスタンスを取得する関数
def get_job_repository() -> JobRepository:
    """
    ジョブリポジトリのインスタンスを取得
    
    Returns:
        JobRepositoryインスタンス
    """
    return JobRepository()
