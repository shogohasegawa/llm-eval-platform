"""
アプリケーションログ設定

詳細なデバッグログを設定します。
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# ルートロガーの設定
def setup_logging(log_level="INFO", log_dir="../logs"):
    """
    アプリケーションのロギング設定を初期化します。
    
    Args:
        log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: ログファイルを保存するディレクトリ
    """
    # ログディレクトリが存在しない場合は作成
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # ログレベルの設定
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # すでにハンドラが設定されている場合はクリア
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # コンソールハンドラの設定
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラの設定
    file_handler = RotatingFileHandler(
        f"{log_dir}/app.log", 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(numeric_level)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    
    # 特定のロガーをより詳細に設定
    llmeval_logger = logging.getLogger("llmeval")
    llmeval_logger.setLevel(logging.DEBUG)  # 常にDEBUGレベルに設定
    
    # FastAPIのロガーを抑制（デフォルトがINFOなので多すぎる）
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # 初期化メッセージ
    llmeval_logger.info(f"ロギングを初期化しました：レベル={log_level}, ディレクトリ={log_dir}")
    
    return root_logger
