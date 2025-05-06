"""
評価指標モジュール

評価指標の実装とAPIエクスポート
"""

import os
import importlib
import importlib.util
import inspect
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Type

from .base import BaseMetric, register_metric, get_metrics_functions, METRIC_REGISTRY

# カスタム評価指標の保存ディレクトリを設定 - プロジェクトのルートディレクトリを基準
# 現在のファイルからプロジェクトルートへの相対パス（../../.. = src/app/metrics -> app -> src -> root）
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
CUSTOM_METRICS_DIR = Path(os.environ.get(
    "CUSTOM_METRICS_DIR", 
    project_root / "external_data/custom_metrics"
))

# ロガーの設定
logger = logging.getLogger(__name__)

def _load_builtin_metrics() -> None:
    """
    組み込み評価指標を動的に読み込むための内部関数
    """
    # 現在のディレクトリ（metricsディレクトリ）
    current_dir = Path(__file__).parent

    # 組み込み評価指標となる全ての.pyファイル
    for file_path in current_dir.glob("*.py"):
        # ファイル名からモジュール名
        module_name = file_path.stem

        # 特殊ファイルは除外
        if module_name.startswith("__") or module_name == "base":
            continue

        # モジュールを読み込む
        module_path = f"app.metrics.{module_name}"
        try:
            module = importlib.import_module(module_path)

            # モジュール内のBaseMetricを継承する全てのクラス
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseMetric) and
                    obj.__module__ == module.__name__ and
                    obj is not BaseMetric):

                    # 重複登録を防ぐための確認
                    if not any(cls is obj for cls in METRIC_REGISTRY.values()):
                        register_metric(obj)

        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import builtin metric module {module_name}: {e}")

def _load_custom_metrics() -> None:
    """
    カスタム評価指標を動的に読み込むための内部関数
    """
    # ディレクトリが存在するか確認
    if not CUSTOM_METRICS_DIR.exists():
        try:
            CUSTOM_METRICS_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"カスタム評価指標ディレクトリを作成しました: {CUSTOM_METRICS_DIR}")
        except Exception as e:
            logger.error(f"カスタム評価指標ディレクトリの作成に失敗しました: {e}")
            return
    else:
        logger.info(f"カスタム評価指標ディレクトリ: {CUSTOM_METRICS_DIR}")
    
    # カスタム評価指標となる全ての.pyファイル
    for file_path in CUSTOM_METRICS_DIR.glob("*.py"):
        try:
            # モジュール名を設定（拡張子なし）
            module_name = file_path.stem
            
            # モジュールをインポート
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                logger.error(f"モジュール {module_name} のスペックまたはローダーが取得できません")
                continue
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 登録された評価指標を確認
            loaded_metrics = []
            for name, cls in METRIC_REGISTRY.items():
                if inspect.getmodule(cls) == module:
                    loaded_metrics.append(name)
            
            if loaded_metrics:
                logger.info(f"カスタム評価指標 {', '.join(loaded_metrics)} をロードしました")
            else:
                logger.warning(f"ファイル {file_path.name} から有効な評価指標が見つかりませんでした")
            
        except Exception as e:
            logger.error(f"カスタム評価指標モジュール {file_path.name} のインポートに失敗しました: {e}")

# 起動時に評価指標を読み込む
_load_builtin_metrics()
_load_custom_metrics()

# APIとして公開する要素
__all__ = [
    "BaseMetric",
    "register_metric",
    "get_metrics_functions",
    "METRIC_REGISTRY",
    "CUSTOM_METRICS_DIR"
]
