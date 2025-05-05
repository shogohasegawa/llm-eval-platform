from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
import json
import logging

from app.api.models import (
    MetricInfo, MetricParameterInfo, MetricsListResponse, 
    MetricCreate, MetricUpdate, MetricResponse, MetricListResponse
)
from app.metrics import METRIC_REGISTRY, get_metrics_functions, BaseMetric
from app.utils.db.database import get_database
# MetricModelはまだ存在しないため、このインポートを削除

# ロガーの設定
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])

class MetricRepository:
    """メトリクスリポジトリクラス"""
    def __init__(self, db):
        self.db = db
        
    def get_all(self) -> List[MetricResponse]:
        """全てのカスタムメトリクスを取得"""
        metrics = self.db.fetch_all("SELECT * FROM metrics ORDER BY created_at DESC")
        return [self._map_to_model(metric) for metric in metrics]
        
    def get_by_id(self, metric_id: str) -> Optional[MetricResponse]:
        """IDによるメトリクス取得"""
        metric = self.db.fetch_one("SELECT * FROM metrics WHERE id = :id", {"id": metric_id})
        if not metric:
            return None
        return self._map_to_model(metric)
        
    def create(self, metric: MetricCreate) -> MetricResponse:
        """新しいメトリクスを作成"""
        metric_id = str(uuid4())
        now = datetime.now()
        
        # パラメータをJSON文字列に変換
        parameters_json = json.dumps(metric.parameters or {}) if metric.parameters else None
        
        # is_higher_betterをブール値からINTEGERに変換
        is_higher_better_int = 1 if metric.is_higher_better else 0
        
        # デバッグログを追加
        logger.info(f"Creating metric with is_higher_better: {metric.is_higher_better} (converted to {is_higher_better_int})")
        
        values = {
            "id": metric_id,
            "name": metric.name,
            "type": metric.type,
            "description": metric.description,
            "is_higher_better": is_higher_better_int,  # INTEGER値として保存
            "parameters": parameters_json,
            "created_at": now,
            "updated_at": now,
        }
        
        self.db.execute(
            """
            INSERT INTO metrics (id, name, type, description, is_higher_better, parameters, created_at, updated_at)
            VALUES (:id, :name, :type, :description, :is_higher_better, :parameters, :created_at, :updated_at)
            """,
            values
        )
        
        return MetricResponse(
            id=metric_id,
            name=metric.name,
            type=metric.type,
            description=metric.description,
            is_higher_better=metric.is_higher_better,
            parameters=metric.parameters,
            created_at=now,
            updated_at=now
        )
        
    def update(self, metric_id: str, metric: MetricUpdate) -> Optional[MetricResponse]:
        """メトリクスの更新"""
        # 既存のメトリクスを取得
        existing = self.get_by_id(metric_id)
        if not existing:
            return None
            
        # 更新するフィールドを準備
        updates = {}
        if metric.name is not None:
            updates["name"] = metric.name
        if metric.type is not None:
            updates["type"] = metric.type
        if metric.description is not None:
            updates["description"] = metric.description
        if metric.is_higher_better is not None:
            # ブール値からINTEGERに変換
            is_higher_better_int = 1 if metric.is_higher_better else 0
            logger.info(f"Updating is_higher_better: {metric.is_higher_better} -> {is_higher_better_int}")
            updates["is_higher_better"] = is_higher_better_int
        if metric.parameters is not None:
            updates["parameters"] = json.dumps(metric.parameters) if metric.parameters else None
            
        # 更新するものがなければ既存のものを返す
        if not updates:
            return existing
            
        # 更新日時を設定
        now = datetime.now()
        updates["updated_at"] = now
        
        # SQLクエリの構築
        update_fields = ", ".join([f"{key} = :{key}" for key in updates.keys()])
        query = f"UPDATE metrics SET {update_fields} WHERE id = :id"
        
        # 更新実行
        values = {**updates, "id": metric_id}
        self.db.execute(query, values)
        
        # 更新後のメトリクスを取得して返す
        return self.get_by_id(metric_id)
        
    def delete(self, metric_id: str) -> bool:
        """メトリクスの削除"""
        # 存在確認
        existing = self.get_by_id(metric_id)
        if not existing:
            return False
            
        # 削除実行
        self.db.execute("DELETE FROM metrics WHERE id = :id", {"id": metric_id})
        return True
        
    def _map_to_model(self, row) -> MetricResponse:
        """データベースの行をモデルにマッピング"""
        try:
            # パラメータをJSONからデコード
            parameters = {}
            if row["parameters"]:
                try:
                    parameters = json.loads(row["parameters"])
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析エラー: {e} in {row['parameters']}")
            
            # is_higher_betterをINTからブール値に変換
            is_higher_better = bool(row["is_higher_better"])
            
            # デバッグログを追加
            logger.info(f"Mapping row to model: is_higher_better (DB): {row['is_higher_better']} -> (bool): {is_higher_better}")
            
            return MetricResponse(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                description=row["description"],
                is_higher_better=is_higher_better,  # ブール値に変換
                parameters=parameters,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        except Exception as e:
            logger.error(f"モデルへのマッピングエラー: {e}, row: {row}")
            raise ValueError(f"モデルへのマッピングエラー: {e}")


@router.get("/available", response_model=MetricsListResponse)
async def get_available_metrics():
    """
    利用可能な組み込み評価指標一覧を返す
    
    Returns:
        MetricsListResponse: 評価指標情報のリスト
    """
    metrics_list: List[MetricInfo] = []
    
    # METRIC_REGISTRYから登録されている評価指標を取得
    for name, metric_cls in METRIC_REGISTRY.items():
        # インスタンスを作成して情報を取得
        metric_instance = metric_cls()
        
        # docstringから説明を取得（可能であれば）
        description = None
        if metric_cls.__doc__:
            description = metric_cls.__doc__.strip()
        
        # パラメータ定義を取得
        param_defs = metric_cls.get_parameter_definitions()
        parameters = {}
        
        # パラメータ定義をAPIモデルに変換
        for param_name, param_def in param_defs.items():
            parameters[param_name] = MetricParameterInfo(
                type=param_def.get("type", "string"),
                description=param_def.get("description"),
                default=param_def.get("default"),
                required=param_def.get("required", False),
                enum=param_def.get("enum")
            )
        
        metrics_list.append(
            MetricInfo(
                name=name,
                description=description,
                parameters=parameters if parameters else None,
                is_higher_better=getattr(metric_instance, "is_higher_better", True)
            )
        )
    
    # 名前でソート
    metrics_list.sort(key=lambda x: x.name)
    
    return MetricsListResponse(metrics=metrics_list)


@router.get("", response_model=MetricListResponse)
async def get_all_metrics(
    db=Depends(get_database)
):
    """
    すべてのカスタムメトリクスを取得する
    
    Returns:
        MetricListResponse: カスタムメトリクス一覧
    """
    repo = MetricRepository(db)
    metrics = repo.get_all()
    return MetricListResponse(metrics=metrics)


@router.get("/{metric_id}", response_model=MetricResponse)
async def get_metric(
    metric_id: str = Path(..., description="メトリクスID"),
    db=Depends(get_database)
):
    """
    特定のメトリクスを取得する
    
    Args:
        metric_id: メトリクスID
        
    Returns:
        MetricResponse: メトリクス情報
    """
    repo = MetricRepository(db)
    metric = repo.get_by_id(metric_id)
    
    if not metric:
        raise HTTPException(status_code=404, detail=f"メトリクスID '{metric_id}' が見つかりません")
        
    return metric


@router.post("", response_model=MetricResponse)
async def create_metric(
    metric: MetricCreate,
    db=Depends(get_database)
):
    """
    新しいカスタムメトリクスを作成する
    
    Args:
        metric: メトリクス作成情報
        
    Returns:
        MetricResponse: 作成されたメトリクス情報
    """
    repo = MetricRepository(db)
    
    # リクエストデータをログに出力（デバッグ用）
    logger.info(f"リクエスト受信: {metric}")
    logger.info(f"isHigherBetter / is_higher_better: {getattr(metric, 'isHigherBetter', None)} / {metric.is_higher_better}")
    
    # isHigherBetterフィールドが存在する場合、is_higher_betterにコピー
    if hasattr(metric, 'isHigherBetter'):
        logger.info(f"isHigherBetter フィールドを検出: {getattr(metric, 'isHigherBetter')}")
        metric.is_higher_better = bool(getattr(metric, 'isHigherBetter'))
        logger.info(f"is_higher_better に設定: {metric.is_higher_better}")
    
    # 名前の重複チェック
    existing_metrics = repo.get_all()
    if any(m.name == metric.name for m in existing_metrics):
        raise HTTPException(status_code=400, detail=f"メトリクス名 '{metric.name}' は既に使用されています")
    
    try:
        return repo.create(metric)
    except Exception as e:
        print(f"メトリクス作成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"メトリクスの作成に失敗しました: {str(e)}")


@router.put("/{metric_id}", response_model=MetricResponse)
async def update_metric(
    metric: MetricUpdate,
    metric_id: str = Path(..., description="メトリクスID"),
    db=Depends(get_database)
):
    """
    既存のメトリクスを更新する
    
    Args:
        metric_id: メトリクスID
        metric: 更新するメトリクス情報
        
    Returns:
        MetricResponse: 更新されたメトリクス情報
    """
    repo = MetricRepository(db)
    
    # リクエストデータをログに出力（デバッグ用）
    logger.info(f"更新リクエスト受信: {metric}")
    logger.info(f"isHigherBetter / is_higher_better: {getattr(metric, 'isHigherBetter', None)} / {metric.is_higher_better}")
    
    # isHigherBetterフィールドが存在する場合、is_higher_betterにコピー
    if hasattr(metric, 'isHigherBetter'):
        logger.info(f"isHigherBetter フィールドを検出: {getattr(metric, 'isHigherBetter')}")
        metric.is_higher_better = bool(getattr(metric, 'isHigherBetter'))
        logger.info(f"is_higher_better に設定: {metric.is_higher_better}")
    
    # 名前の重複チェック（名前を変更する場合のみ）
    if metric.name is not None:
        existing_metrics = repo.get_all()
        if any(m.name == metric.name and m.id != metric_id for m in existing_metrics):
            raise HTTPException(status_code=400, detail=f"メトリクス名 '{metric.name}' は既に使用されています")
    
    try:
        updated_metric = repo.update(metric_id, metric)
        
        if not updated_metric:
            raise HTTPException(status_code=404, detail=f"メトリクスID '{metric_id}' が見つかりません")
            
        return updated_metric
    except Exception as e:
        print(f"メトリクス更新エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"メトリクスの更新に失敗しました: {str(e)}")


@router.delete("/{metric_id}", status_code=204)
async def delete_metric(
    metric_id: str = Path(..., description="メトリクスID"),
    db=Depends(get_database)
):
    """
    メトリクスを削除する
    
    Args:
        metric_id: メトリクスID
    """
    repo = MetricRepository(db)
    result = repo.delete(metric_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"メトリクスID '{metric_id}' が見つかりません")