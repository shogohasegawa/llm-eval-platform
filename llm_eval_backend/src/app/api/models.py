from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import os
from enum import Enum


class ModelConfig(BaseModel):
    """モデル設定"""
    provider: str
    model_name: str
    max_tokens: int
    temperature: Optional[float] = 0.0
    top_p: Optional[float] = 1.0
    additional_params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EvaluationRequest(BaseModel):
    """評価リクエストモデル"""
    datasets: List[str]           # 評価対象のデータセット名一覧
    num_samples: int              # 評価サンプル数
    n_shots: List[int]            # few-shot数リスト
    model: ModelConfig            # フィールド名を model に変更
    async_execution: bool = False  # 非同期実行フラグ（デフォルトは同期実行）


class EvaluationResponse(BaseModel):
    """評価レスポンスモデル"""
    model_info: ModelConfig       # 使用したモデル情報
    metrics: Dict[str, float]     # フラットメトリクス辞書


class JobStatus(str, Enum):
    """ジョブステータス列挙型"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobLogLevel(str, Enum):
    """ジョブログレベル列挙型"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class JobLogEntry(BaseModel):
    """ジョブログエントリモデル"""
    id: str
    job_id: str
    log_level: JobLogLevel
    message: str
    timestamp: datetime


class JobLog(BaseModel):
    """ジョブログモデル"""
    logs: List[JobLogEntry]
    job_id: str


class JobDetail(BaseModel):
    """ジョブ詳細モデル"""
    id: str
    status: JobStatus
    request: EvaluationRequest
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class JobSummary(BaseModel):
    """ジョブ概要モデル（リスト表示用）"""
    id: str
    status: JobStatus
    datasets: List[str]
    model_info: ModelConfig
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """ジョブ一覧レスポンスモデル"""
    jobs: List[JobSummary]
    total: int
    page: int = 1
    page_size: int = 10


class AsyncEvaluationResponse(BaseModel):
    """非同期評価レスポンスモデル"""
    job_id: str
    status: JobStatus
    message: str


class MetricInfo(BaseModel):
    """評価指標情報モデル"""
    name: str                     # 評価指標の名前
    description: Optional[str] = None  # 評価指標の説明（あれば）


class MetricsListResponse(BaseModel):
    """評価指標一覧レスポンスモデル"""
    metrics: List[MetricInfo]     # 利用可能な評価指標一覧


# データセット関連モデル
class DatasetItem(BaseModel):
    """データセットのサンプル項目"""
    id: str
    instruction: str
    input: Optional[str] = None
    output: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DatasetMetadata(BaseModel):
    """データセットのメタデータ"""
    name: str
    description: str
    type: str
    created_at: datetime
    item_count: int
    file_path: str


class DatasetListResponse(BaseModel):
    """データセット一覧レスポンス"""
    datasets: List[DatasetMetadata]


class DatasetDetailResponse(BaseModel):
    """データセット詳細レスポンス"""
    metadata: DatasetMetadata
    items: List[DatasetItem]


class DatasetDeleteResponse(BaseModel):
    """データセット削除レスポンス"""
    success: bool
    message: str
