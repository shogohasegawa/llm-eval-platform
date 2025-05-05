"""
評価指標の抽象基底クラスと登録機能を定義するモジュール
"""
from abc import ABC, abstractmethod
from typing import Dict, Type, Callable, Any, List, Optional, Union


# パラメータ定義の型
ParamDef = Dict[str, Dict[str, Any]]


# メトリクスクラスの登録用ディクショナリ
METRIC_REGISTRY: Dict[str, Type["BaseMetric"]] = {}


class BaseMetric(ABC):
    """
    評価指標の抽象基底クラス

    全ての評価指標はこのクラスを継承して実装する必要がある
    """

    def __init__(self, name: str, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド

        Args:
            name: 評価指標の名前
            parameters: 評価指標のパラメータ
        """
        self.name = name
        self.parameters = parameters or {}

    @abstractmethod
    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        評価スコアを計算する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア
        """
        pass

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        評価指標で使用可能なパラメータ定義を取得
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {}

    def __str__(self) -> str:
        return f"{self.name}"


def register_metric(cls: Type[BaseMetric]) -> Type[BaseMetric]:
    """
    評価指標クラスを登録するデコレータ

    Args:
        cls: 登録する評価指標クラス

    Returns:
        評価指標クラス（デコレータパターン）
    """
    # インスタンスを作成してnameプロパティを取得
    instance = cls()
    name = instance.name
    
    if name in METRIC_REGISTRY:
        raise ValueError(f"Metric '{name}' is already registered")
    
    METRIC_REGISTRY[name] = cls
    return cls


def get_metrics_functions(parameters: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Callable[[str, str], float]]:
    """
    すべての登録済みメトリクス計算関数のディクショナリを取得

    Args:
        parameters: メトリクス名をキー、そのパラメータ辞書を値とするディクショナリ

    Returns:
        Dict[str, Callable]: メトリクス名をキー、計算関数を値とするディクショナリ
    """
    parameters = parameters or {}
    metrics_funcs = {}
    
    for name, metric_cls in METRIC_REGISTRY.items():
        # メトリクスのパラメータがあれば使用、なければ空の辞書
        metric_params = parameters.get(name, {})
        # パラメータ付きでインスタンス化
        metric_instance = metric_cls(parameters=metric_params)
        metrics_funcs[name] = metric_instance.calculate
        
    return metrics_funcs
