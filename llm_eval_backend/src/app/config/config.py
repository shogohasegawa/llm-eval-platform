"""
設定管理モジュール
"""
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional, List


class Settings(BaseSettings):
    """
    アプリケーション設定

    アプリケーション全体で使用する設定パラメータを管理するクラス
    """
    # データセットディレクトリパス - 絶対パスを使用
    project_root: Path = Path(__file__).resolve().parent.parent.parent.parent.parent
    
    # 外部マウントされたデータセットディレクトリを使用
    EXTERNAL_DATASETS_DIR: Path = Path("/external_datasets")
    # テスト用データセットの保存先
    TEST_DATASETS_DIR: Path = Path("/external_datasets/test")
    # n-shot用データセットの保存先
    NSHOT_DATASETS_DIR: Path = Path("/external_datasets/n_shot")
    
    # 結果ディレクトリ
    RESULTS_DIR: Path = project_root / "results/"
    
    # 下位互換性のために残す
    DATASET_DIR: Path = TEST_DATASETS_DIR
    TRAIN_DIR: Path = NSHOT_DATASETS_DIR
    
    # この部分は削除

    # APIとモデル関連
    # Ollamaのエンドポイントもデータベースから取得
    # LITELLM_BASE_URL: str = "http://192.168.101.204:11434/api/generate"
    DEFAULT_MAX_TOKENS: int = 1024
    DEFAULT_TEMPERATURE: float = 0.0
    DEFAULT_TOP_P: float = 1.0
    # タイムアウト設定（秒）
    MODEL_TIMEOUT: float = 60.0
    # リトライ設定
    MODEL_RETRIES: int = 3
    RETRY_BACKOFF_MIN: float = 2.0
    RETRY_BACKOFF_MAX: float = 30.0
    RETRY_BACKOFF_MULTIPLIER: float = 1.5

    # LiteLLM ルーター設定
    ROUTING_STRATEGY: str = "simple-shuffle"  # litellm routerのルーティング戦略
    ROUTER_CACHE_SIZE: int = 100  # ルーターのモデル情報キャッシュサイズ
    ENABLE_FALLBACKS: bool = True  # 自動フォールバックの有効化

    # モデル管理設定
    AUTO_DOWNLOAD_MODELS: bool = True  # モデルの自動ダウンロード設定
    MODEL_CHECK_BEFORE_CALL: bool = True  # 呼び出し前にモデルの存在をチェックするかどうか

    # APIキーとエンドポイントはプロバイダ/モデル設定から取得するため環境変数は使用しない
    # OPENAI_API_BASE: Optional[str] = None 
    # OPENAI_API_KEY: Optional[str] = None
    # ANTHROPIC_API_KEY: Optional[str] = None

    # プロバイダ設定
    ENABLED_PROVIDERS: List[str] = ["ollama", "openai", "anthropic"]
    DEFAULT_PROVIDER: str = "ollama"  # デフォルトプロバイダー
    FALLBACK_PROVIDERS: List[str] = []  # フォールバックプロバイダー（順番に試行）

    # キャッシュ設定
    ENABLE_LITELLM_CACHE: bool = True
    CACHE_EXPIRATION: int = 3600  # 秒
    REDIS_HOST: str = "localhost"  # Redisホスト
    REDIS_PORT: int = 6379  # Redisポート

    # バッチ処理設定
    # TODO: バッチ処理とシングル処理の挙動の違いに関する調査事項
    # - batch_completionとacompletionのAPIキー処理の違いを調査
    # - 各プロバイダのバッチ処理対応状況の確認
    # - バッチ処理のパフォーマンス最適化方法
    BATCH_SIZE: int = 5
    # バッチ処理をサポートするプロバイダのリスト（順次追加予定）
    BATCH_SUPPORTED_PROVIDERS: List[str] = ['openai', 'anthropic', 'claude', 'cohere', 'together', 'groq']
    # バッチ処理が可能なサイズの最大値（プロバイダによって異なる場合あり）
    MAX_BATCH_SIZE: int = 20

    # 評価設定
    DEFAULT_NUM_SAMPLES: int = 10
    DEFAULT_N_SHOTS: list = [0, 2]

    # MLflow 設定
    MLFLOW_TRACKING_URI: Optional[str] = None

    # ロギング設定
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # 環境設定
    PROJECT_ROOT: Optional[Path] = Path('../')  # 明示的にllm_eval_backendの親ディレクトリを指定
    ENV: str = "development"  # development, staging, production

    class Config:
        """Pydantic設定クラス"""
        env_prefix = "LLMEVAL_"  # 環境変数のプレフィックス
        env_file = ".env"  # 環境変数ファイル
        env_file_encoding = "utf-8"

    def initialize_dirs(self) -> None:
        """
        必要なディレクトリを初期化する
        """
        # 必要なディレクトリを作成
        self.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.TEST_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
        self.NSHOT_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"テストデータセットディレクトリ: {self.TEST_DATASETS_DIR.resolve()}")
        print(f"n-shotデータセットディレクトリ: {self.NSHOT_DATASETS_DIR.resolve()}")

    def get_provider_settings(self, provider_name: str) -> Dict[str, Any]:
        """
        特定プロバイダの設定を取得する

        Args:
            provider_name: プロバイダ名

        Returns:
            設定辞書
        """
        provider_settings = {}
        
        # 大文字小文字を区別しないようにする
        provider_name_lower = provider_name.lower()
        
        # すべてのプロバイダでAPIキーとエンドポイントはデータベースから取得する
        # それぞれのプロバイダ設定またはモデル設定にAPIキーとエンドポイントを登録してください
        
        return provider_settings

    def get_routing_config(self) -> Dict[str, Any]:
        """
        ルーティング設定を取得する

        Returns:
            ルーティング設定辞書
        """
        return {
            "strategy": self.ROUTING_STRATEGY,
            "cache_size": self.ROUTER_CACHE_SIZE,
            "enable_fallbacks": self.ENABLE_FALLBACKS,
        }


@lru_cache()
def get_settings() -> Settings:
    """
    設定シングルトンインスタンスを取得

    Returns:
        Settings: 設定インスタンス
    """
    settings = Settings()
    settings.initialize_dirs()
    return settings
