"""
Ollamaモデルダウンロード管理モジュール

Ollamaモデルの非同期ダウンロードと進捗状況の管理を提供します。
ダウンロード情報はデータベースに保存されます。
"""
import asyncio
import aiohttp
import json
import logging
import time
import os
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
from enum import Enum
from app.utils.db.database import get_db

# ロガーの設定
logger = logging.getLogger(__name__)

# Ollamaサービスの接続先をカスタマイズするための環境変数を追加
# プロキシ設計: APIサーバー経由でアクセス（外部からのアクセスはプロキシを経由）
OLLAMA_INTERNAL_URL = os.environ.get("OLLAMA_BASE_URL") # コンテナ間通信用
OLLAMA_EXTERNAL_URL = os.environ.get("OLLAMA_EXTERNAL_URL") # 外部からのアクセス用
OLLAMA_BASE_URL = OLLAMA_INTERNAL_URL # 後方互換性のために維持

# デバッグログ出力
logger.info(f"Ollama接続情報: OLLAMA_INTERNAL_URL={OLLAMA_INTERNAL_URL}, OLLAMA_EXTERNAL_URL={OLLAMA_EXTERNAL_URL}")
logger.info(f"環境変数: OLLAMA_BASE_URL={os.environ.get('OLLAMA_BASE_URL')}")


class DownloadStatus(str, Enum):
    """ダウンロードステータス列挙型"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


# Ollamaモデルダウンロードテーブル作成関数
def init_ollama_download_table():
    """
    Ollamaモデルダウンロードテーブルを初期化
    """
    db = get_db()
    
    try:
        cursor = db.conn.cursor()
        
        # Ollamaモデルダウンロードテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ollama_model_downloads (
            id TEXT PRIMARY KEY,
            model_name TEXT NOT NULL,
            model_id TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            status TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            total_size INTEGER NOT NULL DEFAULT 0,
            downloaded_size INTEGER NOT NULL DEFAULT 0,
            model_size INTEGER NOT NULL DEFAULT 0,
            model_size_gb REAL NOT NULL DEFAULT 0.0,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            digest TEXT,
            model_info TEXT
        )
        ''')
        
        # インデックス作成
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ollama_downloads_model_id
        ON ollama_model_downloads (model_id)
        ''')
        
        db.conn.commit()
        logger.info("Ollamaモデルダウンロードテーブルを初期化しました")
    except Exception as e:
        logger.error(f"Ollamaテーブル初期化エラー: {e}")
        raise


class OllamaModelDownload:
    """
    Ollamaモデルのダウンロード情報とステータスを保持するクラス
    """
    def __init__(self, model_name: str, model_id: str, endpoint: str):
        self.id = str(uuid.uuid4())
        self.model_name = model_name
        self.model_id = model_id
        self.endpoint = endpoint
        self.status = DownloadStatus.PENDING
        self.progress = 0
        self.total_size = 0       # ダウンロード時の転送サイズ (バイト単位)
        self.downloaded_size = 0  # ダウンロード済みの転送サイズ (バイト単位)
        self.model_size = 0       # モデルの実際のサイズ (バイト単位)
        self.model_size_gb = 0.0  # モデルの実際のサイズ (GB単位)
        self.error = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.completed_at = None
        self.digest = None  # ダウンロード中のレイヤーのdigest
        self.model_info = None   # モデルの詳細情報
    
    def to_dict(self) -> Dict[str, Any]:
        """OllamaModelDownloadを辞書に変換"""
        model_info_json = None
        if self.model_info:
            try:
                model_info_json = json.dumps(self.model_info)
            except Exception as e:
                logger.warning(f"モデル情報のJSONエンコードに失敗: {e}")
                
        return {
            "id": self.id,
            "model_name": self.model_name,
            "model_id": self.model_id,
            "endpoint": self.endpoint,
            "status": self.status.value if isinstance(self.status, DownloadStatus) else self.status,
            "progress": self.progress,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "model_size": self.model_size,
            "model_size_gb": self.model_size_gb,
            "error": self.error,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "completed_at": self.completed_at.isoformat() if isinstance(self.completed_at, datetime) else self.completed_at,
            "digest": self.digest,
            "model_info": model_info_json
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OllamaModelDownload':
        """辞書からOllamaModelDownloadを作成"""
        download = cls(
            model_name=data["model_name"],
            model_id=data["model_id"],
            endpoint=data["endpoint"]
        )
        download.id = data["id"]
        download.status = DownloadStatus(data["status"]) if data["status"] in [e.value for e in DownloadStatus] else data["status"]
        download.progress = data["progress"]
        download.total_size = data["total_size"]
        download.downloaded_size = data["downloaded_size"]
        download.model_size = data["model_size"]
        download.model_size_gb = data["model_size_gb"]
        download.error = data["error"]
        
        # 日時フィールドの処理
        if data.get("created_at"):
            download.created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        if data.get("updated_at"):
            download.updated_at = datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"]
        if data.get("completed_at"):
            download.completed_at = datetime.fromisoformat(data["completed_at"]) if isinstance(data["completed_at"], str) else data["completed_at"]
            
        download.digest = data.get("digest")
        
        # モデル情報のJSONデコード
        if data.get("model_info"):
            try:
                download.model_info = json.loads(data["model_info"]) if isinstance(data["model_info"], str) else data["model_info"]
            except json.JSONDecodeError:
                logger.warning(f"モデル情報のJSONデコードに失敗: {data['model_info']}")
                download.model_info = None
        
        return download


class OllamaManager:
    """
    Ollamaモデルのダウンロードを管理するクラス
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """シングルトンパターンでインスタンスを提供"""
        if cls._instance is None:
            cls._instance = super(OllamaManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初期化"""
        if self._initialized:
            return
        
        # データベーステーブルを作成（初回のみ）
        init_ollama_download_table()
        
        # インメモリキャッシュ（進行中のダウンロード用）
        self.downloads = {}  # ダウンロードID: OllamaModelDownload
        
        # データベースから進行中のダウンロードを読み込む
        self._load_active_downloads()
        
        self._initialized = True
    
    def _load_active_downloads(self):
        """進行中のダウンロードをデータベースから読み込む"""
        db = get_db()
        
        try:
            # 進行中または保留中のダウンロードを検索
            active_statuses = [DownloadStatus.PENDING.value, DownloadStatus.DOWNLOADING.value]
            status_placeholders = ", ".join(["?" for _ in active_statuses])
            
            query = f"SELECT * FROM ollama_model_downloads WHERE status IN ({status_placeholders})"
            active_downloads = db.fetch_all(query, tuple(active_statuses))
            
            for download_data in active_downloads:
                download = OllamaModelDownload.from_dict(download_data)
                self.downloads[download.id] = download
                logger.info(f"進行中のダウンロードを読み込みました: {download.id}, {download.model_name}")
        except Exception as e:
            logger.error(f"進行中のダウンロードの読み込みに失敗: {e}")
    
    def _save_download(self, download: OllamaModelDownload):
        """ダウンロード情報をデータベースに保存"""
        db = get_db()
        download_dict = download.to_dict()
        
        try:
            # 既存のレコードを確認
            existing = db.fetch_one("SELECT id FROM ollama_model_downloads WHERE id = ?", (download.id,))
            
            if existing:
                # 既存レコードを更新
                update_fields = []
                update_values = []
                
                for key, value in download_dict.items():
                    if key != 'id':
                        update_fields.append(f"{key} = ?")
                        update_values.append(value)
                
                # WHERE句のID
                update_values.append(download.id)
                
                update_query = f"UPDATE ollama_model_downloads SET {', '.join(update_fields)} WHERE id = ?"
                db.execute(update_query, tuple(update_values))
            else:
                # 新規レコードを挿入
                fields = list(download_dict.keys())
                placeholders = ["?" for _ in fields]
                values = [download_dict[field] for field in fields]
                
                insert_query = f"INSERT INTO ollama_model_downloads ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
                db.execute(insert_query, tuple(values))
            
            db.commit()
        except Exception as e:
            logger.error(f"ダウンロード情報の保存に失敗: {e}")
            db.rollback()
            raise
    
    async def download_model(self, model_name: str, model_id: str, endpoint: str) -> Dict[str, Any]:
        """
        Ollamaモデルの非同期ダウンロードを開始する
        
        Args:
            model_name: ダウンロードするモデル名
            model_id: 関連するモデルID
            endpoint: Ollamaサーバーのエンドポイント
            
        Returns:
            ダウンロード情報
        """
        # エンドポイントにプロトコルが含まれていなければ追加
        if not endpoint.startswith(('http://', 'https://')):
            endpoint = f"http://{endpoint}"
        
        # ダウンロード情報を作成
        download = OllamaModelDownload(model_name, model_id, endpoint)
        self.downloads[download.id] = download
        
        # データベースに保存
        self._save_download(download)
        
        # エンドポイントが正しい形式かチェック
        if not endpoint.endswith('/'):
            endpoint = f"{endpoint}/"
        
        # 非同期でダウンロードを実行
        asyncio.create_task(self._download_model_task(download.id))
        
        return self._download_to_dict(download)
    
    async def _download_model_task(self, download_id: str):
        """
        非同期でモデルをダウンロードするタスク
        
        Args:
            download_id: ダウンロードID
        """
        download = self.downloads.get(download_id)
        if not download:
            logger.error(f"ダウンロードIDが見つかりません: {download_id}")
            return
        
        try:
            # ダウンロードステータスを更新
            download.status = DownloadStatus.DOWNLOADING
            download.updated_at = datetime.now()
            
            # DB更新
            self._save_download(download)
            
            # Ollamaのpull APIを呼び出してモデルをダウンロード
            # エンドポイントの末尾のスラッシュを確認
            base_url = download.endpoint
            if not base_url.endswith('/'):
                base_url += '/'
            
            # 正しいAPIエンドポイントを構築
            api_url = f"{base_url}api/pull"
            
            # 詳細ログ - ダウンロード開始情報
            logger.info(f"[OLLAMA_DEBUG] ダウンロード開始: ID={download.id}, モデル={download.model_name}")
            logger.info(f"[OLLAMA_DEBUG] URL={api_url}, エンドポイント={download.endpoint}")
            logger.info(f"[OLLAMA_DEBUG] 現在のステータス={download.status}, 進捗={download.progress}%")
            
            # ClientSessionのロギング設定
            trace_config = aiohttp.TraceConfig()
            
            async def on_request_start(session, trace_config_ctx, params):
                logger.info(f"[OLLAMA_HTTP] リクエスト開始: {params.method} {params.url}")
            
            async def on_request_end(session, trace_config_ctx, params):
                logger.info(f"[OLLAMA_HTTP] リクエスト完了: {params.method} {params.url}, ステータス={params.response.status}")
            
            trace_config.on_request_start.append(on_request_start)
            trace_config.on_request_end.append(on_request_end)
            
            # タイムアウト設定
            timeout = aiohttp.ClientTimeout(total=1800)  # 30分
            
            async with aiohttp.ClientSession(trace_configs=[trace_config], timeout=timeout) as session:
                payload = {
                    "model": download.model_name,
                    "stream": True
                }
                
                logger.info(f"[OLLAMA_DEBUG] リクエストペイロード: {payload}")
                
                async with session.post(api_url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollamaモデルのダウンロードに失敗: {error_text}")
                        logger.error(f"リクエスト先URL: {api_url}")
                        logger.error(f"リクエスト内容: {payload}")
                        download.status = DownloadStatus.FAILED
                        download.error = f"HTTP エラー {response.status}: {error_text}"
                        download.updated_at = datetime.now()
                        
                        # DB更新
                        self._save_download(download)
                        return
                    
                    # レスポンスを行ごとに読み込む（ストリーミングレスポンス）
                    last_db_update = time.time()  # 最後のDB更新時間
                    
                    async for line in response.content:
                        if not line:
                            continue
                        
                        # JSONパース
                        try:
                            # 受信したライン内容をロギング
                            if len(line) < 500:  # 大きすぎる場合は省略
                                logger.info(f"[OLLAMA_STREAM] 受信データ: {line.decode('utf-8', errors='replace')}")
                            else:
                                logger.info(f"[OLLAMA_STREAM] 受信データ: {line[:500].decode('utf-8', errors='replace')}... (省略)")
                            
                            data = json.loads(line)
                            
                            # エラーチェックを最初に行う
                            if 'error' in data:
                                error_msg = data.get('error')
                                logger.error(f"[OLLAMA_ERROR] エラー検出: {error_msg}")
                                download.error = error_msg
                                download.status = DownloadStatus.FAILED
                                download.updated_at = datetime.now()
                                
                                # エラー発生時は即座にDBに保存
                                self._save_download(download)
                                # エラーが見つかった場合はループを抜ける
                                break
                            
                            # ステータスを更新
                            status = data.get("status")
                            status_changed = False
                            
                            # 詳細な進捗情報のログ出力
                            logger.info(f"[OLLAMA_PROGRESS] ステータス: {status}, データ: {data}")
                            
                            if status == "pulling manifest":
                                logger.info(f"[OLLAMA_STATE] マニフェスト取得中: {download.model_name}, モデルID: {download.id}")
                                status_changed = True
                            
                            elif status == "downloading":
                                # ダウンロード進捗状況の更新
                                old_progress = download.progress
                                download.digest = data.get("digest")
                                download.total_size = data.get("total", 0)
                                download.downloaded_size = data.get("completed", 0)
                                
                                if download.total_size > 0:
                                    download.progress = int((download.downloaded_size / download.total_size) * 100)
                                
                                # 進捗情報のロギング
                                logger.info(f"[OLLAMA_DOWNLOAD] 進捗: {download.progress}%, サイズ: {download.downloaded_size}/{download.total_size} bytes, ダイジェスト: {download.digest}")
                                
                                # 進捗が変わった場合のみDBを更新 (5秒に1回まで)
                                current_time = time.time()
                                if (old_progress != download.progress and current_time - last_db_update > 5) or download.progress % 10 == 0:
                                    self._save_download(download)
                                    last_db_update = current_time
                                    status_changed = True
                                    logger.info(f"[OLLAMA_DB] ダウンロード進捗をDBに保存: {download.progress}%")
                                
                                logger.debug(f"ダウンロード進捗: {download.model_name}, {download.progress}%, {download.downloaded_size}/{download.total_size}")
                            
                            elif status == "verifying sha256 digest":
                                logger.info(f"[OLLAMA_STATE] SHA256ダイジェスト検証中: {download.model_name}, モデルID: {download.id}")
                                status_changed = True
                            
                            elif status == "writing manifest":
                                logger.info(f"[OLLAMA_STATE] マニフェスト書き込み中: {download.model_name}, モデルID: {download.id}")
                                status_changed = True
                            
                            elif status == "removing any unused layers":
                                logger.info(f"[OLLAMA_STATE] 未使用レイヤー削除中: {download.model_name}, モデルID: {download.id}")
                                status_changed = True
                            
                            elif status == "success":
                                # ダウンロード完了
                                download.status = DownloadStatus.COMPLETED
                                download.progress = 100
                                download.completed_at = datetime.now()
                                logger.info(f"[OLLAMA_SUCCESS] ダウンロード完了: {download.model_name}, モデルID: {download.id}")
                                status_changed = True
                                
                                # モデルの実際のサイズを取得するため、tags APIを呼び出す
                                try:
                                    base_url = download.endpoint
                                    if not base_url.endswith('/'):
                                        base_url += '/'
                                    tags_url = f"{base_url}api/tags"
                                    
                                    async with aiohttp.ClientSession() as tags_session:
                                        async with tags_session.get(tags_url) as tags_response:
                                            if tags_response.status == 200:
                                                tags_data = await tags_response.json()
                                                logger.info(f"[OLLAMA_SIZE_DEBUG] タグレスポンス全体: {json.dumps(tags_data)}")

                                                # モデル情報を確認
                                                found_model = False
                                                for model_info in tags_data.get("models", []):
                                                    logger.info(f"[OLLAMA_SIZE_DEBUG] モデル情報: {json.dumps(model_info)}")
                                                    model_name_in_list = model_info.get("name", "")

                                                    # 完全一致 または 前方一致（モデル名:タグ）のパターンをチェック
                                                    if (model_name_in_list == download.model_name or
                                                        model_name_in_list.startswith(f"{download.model_name}:") or
                                                        download.model_name.startswith(f"{model_name_in_list}:")):

                                                        found_model = True
                                                        # モデル情報の詳細ログ
                                                        logger.info(f"[OLLAMA_SIZE_DEBUG] 一致モデル: 検索={download.model_name}, 見つかった={model_name_in_list}, 情報: {json.dumps(model_info)}")
                                                        logger.info(f"[OLLAMA_SIZE_DEBUG] サイズフィールド: {model_info.get('size')}, 型: {type(model_info.get('size'))}")

                                                        # モデルサイズをセット (バイト単位)
                                                        download.model_size = model_info.get("size", 0)
                                                        # GBに変換 (小数点2桁まで)
                                                        if download.model_size > 0:
                                                            download.model_size_gb = round(download.model_size / (1024 * 1024 * 1024), 2)
                                                        else:
                                                            # モデルサイズが0または存在しない場合はダウンロードサイズを使用
                                                            if download.total_size > 0:
                                                                logger.info(f"[OLLAMA_SIZE_DEBUG] モデルサイズが0のためダウンロードサイズを使用: {download.total_size} bytes")
                                                                download.model_size = download.total_size
                                                                download.model_size_gb = round(download.model_size / (1024 * 1024 * 1024), 2)

                                                        download.model_info = model_info
                                                        logger.info(f"[OLLAMA_SIZE_DEBUG] 最終セットされたモデルサイズ: {download.model_size} bytes, {download.model_size_gb} GB")
                                                        break

                                                # モデルが見つからなかった場合のログ
                                                if not found_model:
                                                    logger.warning(f"[OLLAMA_SIZE_DEBUG] モデル {download.model_name} が見つかりませんでした。ダウンロードサイズを使用します")
                                                    # ダウンロードサイズを使用
                                                    if download.total_size > 0:
                                                        download.model_size = download.total_size
                                                        download.model_size_gb = round(download.model_size / (1024 * 1024 * 1024), 2)
                                                        logger.info(f"[OLLAMA_SIZE_DEBUG] ダウンロードサイズから設定: {download.model_size} bytes, {download.model_size_gb} GB")
                                                
                                                # DB更新
                                                self._save_download(download)
                                except Exception as model_size_error:
                                    logger.error(f"モデルサイズの取得に失敗: {str(model_size_error)}")
                            
                            # 更新時間を更新
                            download.updated_at = datetime.now()
                            
                            # 重要なステータス変更時はDB更新
                            if status_changed:
                                self._save_download(download)
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSONデコードエラー: {e}, ライン: {line}")
                        except Exception as e:
                            logger.error(f"ダウンロード処理中のエラー: {e}")
            
            # ダウンロード状態の詳細を記録
            logger.info(f"[OLLAMA_FINISH] ダウンロード処理終了ステータス: {download.status}, プログレス: {download.progress}%, エラー: {download.error}")
            
            # モデル名とIDを明示
            model_info = f"モデル: {download.model_name}, ID: {download.id}"
            
            # エラーが既に設定されている場合は失敗として扱う
            if download.error:
                logger.error(f"[OLLAMA_FINISH] エラーが検出されたため失敗: {model_info}, エラー: {download.error}")
                download.status = DownloadStatus.FAILED
                download.updated_at = datetime.now()
                self._save_download(download)
                return
            
            # ダウンロードが既に成功と明示的にマークされている場合
            if download.status == DownloadStatus.COMPLETED:
                logger.info(f"[OLLAMA_FINISH] 明示的に成功完了マーク済み: {model_info}")
                
                # DB更新（最終ステータスを確実に保存）
                download.updated_at = datetime.now()
                self._save_download(download)
            else:
                # 明示的な成功メッセージを受け取らなかった場合の状態判定
                logger.info(f"[OLLAMA_FINISH] 状態判定開始: HTTP状態={response.status}, エラー有無={bool(download.error)}")
                
                # 進捗のチェック - 0%のままならエラーの可能性あり
                if download.progress == 0:
                    logger.warning(f"[OLLAMA_WARNING] 進捗が0%のままでダウンロード終了: {model_info}")
                    download.status = DownloadStatus.FAILED
                    download.error = "ダウンロードが完了しませんでした（進捗0%）"
                    download.updated_at = datetime.now()
                    logger.error(f"[OLLAMA_ERROR] ダウンロード失敗: {model_info}, エラー: {download.error}")
                # HTTP状態以外のエラーの確認
                elif response.status != 200:
                    # HTTP以外のエラーかレスポンスにエラーがある場合
                    download.status = DownloadStatus.FAILED
                    download.error = f"HTTP エラー: {response.status}"
                    download.updated_at = datetime.now()
                    logger.error(f"[OLLAMA_ERROR] ダウンロード失敗: {model_info}, エラー: {download.error}")
                else:
                    # 正常なHTTPレスポンスで、明示的なエラーがない場合は成功として処理
                    download.status = DownloadStatus.COMPLETED
                    download.progress = 100
                    download.completed_at = datetime.now()
                    download.updated_at = datetime.now()
                    logger.info(f"[OLLAMA_SUCCESS] 暗黙的なダウンロード完了: {model_info}")
                
                # DB更新
                logger.info(f"[OLLAMA_DB] 最終状態をDBに保存: status={download.status}, progress={download.progress}%, error={download.error}")
                self._save_download(download)
        
        except Exception as e:
            # 例外発生時
            download.status = DownloadStatus.FAILED
            download.error = str(e)
            download.updated_at = datetime.now()
            
            # 例外の詳細を記録
            logger.error(f"[OLLAMA_EXCEPTION] モデル: {download.model_name}, ID: {download.id}")
            logger.error(f"[OLLAMA_EXCEPTION] エラー詳細: {str(e)}")
            logger.error(f"[OLLAMA_EXCEPTION] スタックトレース:", exc_info=True)
            
            # DB更新
            logger.info(f"[OLLAMA_DB] 例外発生後の状態をDBに保存: status={download.status}, error={download.error}")
            self._save_download(download)
    
    def get_download(self, download_id: str) -> Optional[Dict[str, Any]]:
        """
        ダウンロード情報を取得
        
        Args:
            download_id: ダウンロードID
            
        Returns:
            ダウンロード情報辞書またはNone
        """
        # まずメモリキャッシュを確認（進行中のダウンロード）
        download = self.downloads.get(download_id)
        if download:
            return self._download_to_dict(download)
        
        # メモリになければDBから取得
        db = get_db()
        db_download = db.fetch_one("SELECT * FROM ollama_model_downloads WHERE id = ?", (download_id,))
        
        if not db_download:
            return None
        
        return self._download_to_dict(OllamaModelDownload.from_dict(db_download))
    
    def get_downloads_by_model_id(self, model_id: str) -> List[Dict[str, Any]]:
        """
        モデルIDに関連するダウンロード情報をすべて取得
        
        Args:
            model_id: モデルID
            
        Returns:
            ダウンロード情報辞書のリスト
        """
        # DBからダウンロード情報を取得
        db = get_db()
        db_downloads = db.fetch_all(
            "SELECT * FROM ollama_model_downloads WHERE model_id = ? ORDER BY created_at DESC", 
            (model_id,)
        )
        
        return [self._download_to_dict(OllamaModelDownload.from_dict(download)) for download in db_downloads]
    
    def get_all_downloads(self) -> List[Dict[str, Any]]:
        """
        すべてのダウンロード情報を取得
        
        Returns:
            ダウンロード情報辞書のリスト
        """
        # DBからすべてのダウンロード情報を取得
        db = get_db()
        db_downloads = db.fetch_all("SELECT * FROM ollama_model_downloads ORDER BY created_at DESC")
        
        return [self._download_to_dict(OllamaModelDownload.from_dict(download)) for download in db_downloads]
    
    def _download_to_dict(self, download: OllamaModelDownload) -> Dict[str, Any]:
        """
        ダウンロードオブジェクトを辞書に変換
        
        Args:
            download: ダウンロードオブジェクト
            
        Returns:
            ダウンロード情報辞書
        """
        return {
            "id": download.id,
            "model_name": download.model_name,
            "model_id": download.model_id,
            "endpoint": download.endpoint,
            "status": download.status,
            "progress": download.progress,
            "total_size": download.total_size,
            "downloaded_size": download.downloaded_size,
            "model_size": download.model_size,
            "model_size_gb": download.model_size_gb,
            "error": download.error,
            "created_at": download.created_at.isoformat(),
            "updated_at": download.updated_at.isoformat(),
            "completed_at": download.completed_at.isoformat() if download.completed_at else None,
            "digest": download.digest,
            "model_info": download.model_info
        }


# シングルトンインスタンスを取得する関数
def get_ollama_manager() -> OllamaManager:
    """
    OllamaManagerのシングルトンインスタンスを取得
    
    Returns:
        OllamaManagerインスタンス
    """
    return OllamaManager()