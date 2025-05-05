"""
データベース接続モジュール

SQLiteデータベースへの接続を管理します。
コンテナ外のマウントディレクトリにデータベースファイルを保存します。
"""
import os
import sqlite3
from pathlib import Path
import logging
from typing import Optional, Dict, List, Any, Union

# ロガーの設定
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    SQLiteデータベース接続を管理するクラス
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """シングルトンパターンでインスタンスを提供"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None):
        """
        データベースマネージャを初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        if self._initialized:
            return
        
        # デフォルトではコンテナ外の /external_data にデータベースファイルを保存
        self.db_path = db_path or os.environ.get(
            "LLMEVAL_DB_PATH", 
            "/external_data/llm_eval.db"
        )
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        logger.info(f"データベースパス: {self.db_path}")
        
        # データベースに接続
        self.conn = None
        self.connect()
        
        # テーブルの初期化
        self.init_tables()
        
        self._initialized = True
    
    def connect(self):
        """データベースに接続"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # 行をディクショナリとして取得できるように設定
            self.conn.row_factory = sqlite3.Row
            logger.info("データベースに接続しました")
        except sqlite3.Error as e:
            logger.error(f"データベース接続エラー: {e}")
            raise
    
    def init_tables(self):
        """必要なテーブルを初期化"""
        try:
            cursor = self.conn.cursor()
            
            # プロバイダーテーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS providers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                endpoint TEXT,
                api_key TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # モデルテーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                name TEXT NOT NULL,
                display_name TEXT,
                description TEXT,
                endpoint TEXT,
                api_key TEXT,
                parameters TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE CASCADE
            )
            ''')
            
            # 評価ジョブテーブル - 新規追加
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL, -- pending, running, completed, failed
                request_data TEXT NOT NULL, -- JSON形式で保存した評価リクエストデータ
                result_data TEXT, -- JSON形式で保存した評価結果データ (完了時のみ)
                error_message TEXT, -- エラーメッセージ (失敗時のみ)
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT -- 完了時刻 (完了時のみ)
            )
            ''')
            
            # ジョブログテーブル - 新規追加
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_logs (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                log_level TEXT NOT NULL, -- info, warning, error
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES evaluation_jobs (id) ON DELETE CASCADE
            )
            ''')
            
            # メトリクステーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                is_higher_better INTEGER NOT NULL DEFAULT 1,
                parameters TEXT, -- JSON形式で保存したパラメータ
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # 推論テーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS inferences (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                dataset_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                status TEXT NOT NULL, -- pending, running, completed, failed
                progress INTEGER NOT NULL DEFAULT 0,
                metrics TEXT, -- JSON形式で保存したメトリクスデータ
                parameters TEXT, -- JSON形式で保存したパラメータ（max_tokens, temperature, top_p, num_samplesなど）
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT,
                FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE CASCADE,
                FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE
            )
            ''')
            
            # 推論結果テーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS inference_results (
                id TEXT PRIMARY KEY,
                inference_id TEXT NOT NULL,
                input TEXT NOT NULL,
                expected_output TEXT,
                actual_output TEXT NOT NULL,
                metrics TEXT, -- JSON形式で保存したメトリクスデータ
                latency REAL, -- 推論にかかった時間（ミリ秒）
                token_count INTEGER, -- トークン数
                created_at TEXT NOT NULL,
                FOREIGN KEY (inference_id) REFERENCES inferences (id) ON DELETE CASCADE
            )
            ''')
            
            self.conn.commit()
            logger.info("テーブルを初期化しました")
        except sqlite3.Error as e:
            logger.error(f"テーブル初期化エラー: {e}")
            raise
    
    def execute(self, query: str, params: tuple = ()):
        """
        SQLクエリを実行
        
        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ
            
        Returns:
            カーソルオブジェクト
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            logger.error(f"クエリ実行エラー: {query}, パラメータ: {params}, エラー: {e}")
            raise
    
    def commit(self):
        """トランザクションをコミット"""
        self.conn.commit()
    
    def rollback(self):
        """トランザクションをロールバック"""
        self.conn.rollback()
    
    def close(self):
        """接続を閉じる"""
        if self.conn:
            self.conn.close()
            logger.info("データベース接続を閉じました")
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        単一行を取得してディクショナリとして返す
        
        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ
            
        Returns:
            結果行のディクショナリまたはNone
        """
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        複数行を取得してディクショナリのリストとして返す
        
        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ
            
        Returns:
            結果行のディクショナリのリスト
        """
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
        
    def encode_json(self, data: Any) -> Optional[str]:
        """
        データをJSON文字列にエンコードする
        
        Args:
            data: エンコードするデータ
            
        Returns:
            JSON文字列または None
        """
        if data is None:
            return None
        return json.dumps(data)
        
    def decode_json(self, json_str: Optional[str]) -> Any:
        """
        JSON文字列をデコードする
        
        Args:
            json_str: デコードするJSON文字列
            
        Returns:
            デコードされたデータまたは None
        """
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error(f"JSONデコードエラー: {json_str}")
            return None


# シングルトンインスタンスを取得する関数
def get_db() -> DatabaseManager:
    """
    データベースマネージャのシングルトンインスタンスを取得
    
    Returns:
        DatabaseManagerインスタンス
    """
    return DatabaseManager()


# FastAPI依存関数
async def get_database():
    """
    FastAPI依存性注入用のデータベースを取得する関数
    
    Returns:
        DatabaseManagerインスタンス
    """
    db = get_db()
    try:
        yield db
    finally:
        # 明示的なクローズなどは必要なければコメントアウト可能
        pass
