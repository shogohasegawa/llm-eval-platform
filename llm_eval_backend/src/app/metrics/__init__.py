"""
評価指標モジュール

評価指標の実装とAPIエクスポート
"""

import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, List, Type

from .base import BaseMetric, register_metric, get_metrics_functions, METRIC_REGISTRY


def _load_metrics() -> None:
    """
    評価指標を動的に読み込むための内部関数
    """
    # 現在のディレクトリ（metricsディレクトリ）
    current_dir = Path(__file__).parent

    # 評価指標となる全ての.pyファイル
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
            print(f"Failed to import metric module {module_name}: {e}")


# 起動時に評価指標を読み込む
_load_metrics()

# APIとして公開する要素
__all__ = [
    "BaseMetric",
    "register_metric",
    "get_metrics_functions",
    "METRIC_REGISTRY"
]
