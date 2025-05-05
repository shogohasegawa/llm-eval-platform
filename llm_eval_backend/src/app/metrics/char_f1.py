"""
文字ベースのF1スコア評価指標モジュール
"""
from .base import BaseMetric, register_metric
from fuzzywuzzy import fuzz


@register_metric
class CharF1(BaseMetric):
    """
    文字ベースのF1スコア評価指標
    """

    def __init__(self, parameters=None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="char_f1", parameters=parameters)

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        文字ベースのF1スコアで評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（0.0-1.0）
        """
        return fuzz.token_sort_ratio(hypothesis.strip(), reference.strip()) / 100.0
