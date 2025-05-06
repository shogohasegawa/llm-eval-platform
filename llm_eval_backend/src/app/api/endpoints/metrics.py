from fastapi import APIRouter, HTTPException, Depends, Path, Query, File, UploadFile
from typing import List, Dict, Any, Optional
import logging
import os
import inspect
import importlib.util
import sys
from pathlib import Path as FilePath

from app.api.models import (
    MetricInfo, MetricParameterInfo, MetricsListResponse, 
    MetricResponse
)
from app.metrics import METRIC_REGISTRY, get_metrics_functions, BaseMetric, CUSTOM_METRICS_DIR

# ロガーの設定
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/available", response_model=MetricsListResponse)
async def get_available_metrics():
    """
    利用可能な評価指標一覧を返す（組み込みと外部の両方）
    
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
        
        # メトリクスソースファイルのパス - カスタムディレクトリにあるかどうかを確認
        source_file = inspect.getsourcefile(metric_cls)
        is_custom = False
        if source_file:
            try:
                # カスタムディレクトリのメトリクスかどうかをチェック
                is_custom = str(CUSTOM_METRICS_DIR) in source_file
            except:
                is_custom = False
        
        metrics_list.append(
            MetricInfo(
                name=name,
                description=description,
                parameters=parameters if parameters else None,
                is_higher_better=getattr(metric_instance, "is_higher_better", True),
                is_custom=is_custom
            )
        )
    
    # 名前でソート
    metrics_list.sort(key=lambda x: x.name)
    
    return MetricsListResponse(metrics=metrics_list)

@router.get("/available/{metric_name}/code", response_model=Dict[str, str])
async def get_metric_code(metric_name: str = Path(..., description="評価指標名")):
    """
    特定の評価指標のソースコードを取得する
    
    Args:
        metric_name: 評価指標名
        
    Returns:
        Dict[str, str]: ソースコードを含む辞書
    """
    # 指標が存在するか確認
    if metric_name not in METRIC_REGISTRY:
        raise HTTPException(status_code=404, detail=f"評価指標 '{metric_name}' が見つかりません")
    
    metric_cls = METRIC_REGISTRY[metric_name]
    
    try:
        # クラスのソースファイルを取得
        source_file = inspect.getsourcefile(metric_cls)
        if not source_file:
            raise HTTPException(status_code=404, detail="ソースファイルが見つかりません")
        
        # ソースコードを取得
        with open(source_file, "r", encoding="utf-8") as f:
            source_code = f.read()
        
        return {
            "filename": os.path.basename(source_file),
            "path": source_file,
            "code": source_code,
            "class_name": metric_cls.__name__
        }
    except Exception as e:
        logger.error(f"ソースコード取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ソースコードの取得に失敗しました: {str(e)}")

@router.post("/upload", response_model=Dict[str, str])
async def upload_metric_file(file: UploadFile = File(...)):
    """
    カスタム評価指標のPythonファイルをアップロードする
    
    Args:
        file: アップロードするPythonファイル
        
    Returns:
        Dict[str, str]: 結果情報を含む辞書
    """
    # ファイル形式チェック
    if not file.filename.endswith('.py'):
        raise HTTPException(status_code=400, detail="Pythonファイル(.py)のみアップロード可能です")
    
    try:
        # ファイル内容を読み取り
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # 安全性チェック（基本的なチェックのみ）
        if "import os" in file_content and ("system(" in file_content or "popen(" in file_content):
            raise HTTPException(status_code=400, detail="セキュリティ上の問題があるコードが含まれています")
        
        # BaseMetricの継承チェック
        if "BaseMetric" not in file_content or "register_metric" not in file_content:
            raise HTTPException(status_code=400, detail="BaseMetricを継承し、register_metricデコレータを使用する必要があります")
        
        # ファイル保存パス
        safe_filename = os.path.basename(file.filename)
        file_path = CUSTOM_METRICS_DIR / safe_filename
        
        # ファイルを保存
        with open(file_path, "wb") as f:
            # ファイルポインタを先頭に戻す
            await file.seek(0)
            # 内容を書き込み
            f.write(await file.read())
        
        # モジュールのインポートを試行
        try:
            # モジュール名を設定（拡張子なし）
            module_name = os.path.splitext(safe_filename)[0]
            
            # モジュールをインポート
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                raise ImportError(f"モジュール {module_name} のスペックまたはローダーが取得できません")
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 登録された評価指標を確認
            new_metrics = []
            for name, cls in METRIC_REGISTRY.items():
                if inspect.getmodule(cls) == module:
                    new_metrics.append(name)
            
            if not new_metrics:
                raise HTTPException(status_code=400, detail="有効な評価指標が見つかりませんでした")
            
            # メトリクス名をカンマ区切りの文字列に変換
            metrics_str = ",".join(new_metrics)
            
            return {
                "message": "評価指標のアップロードに成功しました",
                "filename": safe_filename,
                "path": str(file_path),
                "metrics": metrics_str
            }
        except Exception as import_error:
            # インポートエラーの場合はファイルを削除
            os.remove(file_path)
            logger.error(f"モジュールのインポートエラー: {str(import_error)}")
            raise HTTPException(status_code=400, detail=f"評価指標モジュールが正しくインポートできません: {str(import_error)}")
            
    except Exception as e:
        logger.error(f"評価指標アップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"評価指標のアップロードに失敗しました: {str(e)}")


@router.delete("/{metric_name}", response_model=Dict[str, str])
async def delete_metric(metric_name: str = Path(..., description="削除する評価指標名")):
    """
    カスタム評価指標を削除する
    
    Args:
        metric_name: 削除する評価指標名
        
    Returns:
        Dict[str, str]: 結果を含む辞書
    """
    # 指標が存在するか確認
    if metric_name not in METRIC_REGISTRY:
        raise HTTPException(status_code=404, detail=f"評価指標 '{metric_name}' が見つかりません")
    
    metric_cls = METRIC_REGISTRY[metric_name]
    
    try:
        # ソースファイルのパスを取得
        source_file = inspect.getsourcefile(metric_cls)
        if not source_file:
            raise HTTPException(status_code=404, detail="ソースファイルが見つかりません")
        
        # カスタム評価指標かどうかを確認
        if str(CUSTOM_METRICS_DIR) not in source_file:
            raise HTTPException(status_code=403, detail="組み込み評価指標は削除できません")
        
        # Pythonファイルを削除
        file_path = FilePath(source_file)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"評価指標ファイル {source_file} を削除しました")
            
            # 対応するpycファイルを探して削除
            pycache_dir = file_path.parent / "__pycache__"
            if pycache_dir.exists():
                filename_base = file_path.stem
                for pyc_file in pycache_dir.glob(f"{filename_base}*.pyc"):
                    pyc_file.unlink()
                    logger.info(f"コンパイル済みファイル {pyc_file} を削除しました")
            
            # プロセスの再起動は必要ないが、モジュールとメトリクスレジストリからエントリを削除
            module_name = metric_cls.__module__
            if module_name in sys.modules:
                # モジュールを削除
                del sys.modules[module_name]
                logger.info(f"モジュール {module_name} をsys.modulesから削除しました")
            
            # レジストリから削除
            if metric_name in METRIC_REGISTRY:
                del METRIC_REGISTRY[metric_name]
                logger.info(f"評価指標 {metric_name} をレジストリから削除しました")
            
            return {
                "message": f"評価指標 '{metric_name}' を削除しました",
                "name": metric_name,
                "path": str(source_file)
            }
        else:
            # ファイルが存在しない場合はレジストリからのみ削除
            if metric_name in METRIC_REGISTRY:
                del METRIC_REGISTRY[metric_name]
                logger.info(f"評価指標 {metric_name} をレジストリから削除しました（ファイルは見つかりませんでした）")
            
            return {
                "message": f"評価指標 '{metric_name}' をレジストリから削除しました（ファイルは見つかりませんでした）",
                "name": metric_name
            }
        
    except Exception as e:
        logger.error(f"評価指標削除エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"評価指標の削除に失敗しました: {str(e)}")


@router.get("", response_model=MetricsListResponse)
async def get_all_metrics():
    """
    すべてのカスタムメトリクスを取得する
    
    Returns:
        MetricsListResponse: カスタムメトリクス一覧
    """
    metrics_list = []
    
    for name, metric_cls in METRIC_REGISTRY.items():
        # メトリクスソースファイルのパス
        source_file = inspect.getsourcefile(metric_cls)
        
        # カスタムメトリクスのみをフィルタリング
        if not source_file or str(CUSTOM_METRICS_DIR) not in source_file:
            continue
            
        # インスタンスを作成
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
                is_higher_better=getattr(metric_instance, "is_higher_better", True),
                is_custom=True  # カスタムディレクトリから読み込んだものなので常にTrue
            )
        )
    
    # 名前でソート
    metrics_list.sort(key=lambda x: x.name)
    
    return MetricsListResponse(metrics=metrics_list)