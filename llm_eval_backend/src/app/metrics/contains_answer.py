"""
回答を含むかどうかの評価指標モジュール
"""
from .base import BaseMetric, register_metric


@register_metric
class ContainsAnswer(BaseMetric):
    """
    回答を含むかどうかの評価指標
    """

    def __init__(self, parameters=None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="contains_answer", parameters=parameters)

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        予測文字列が正解を含んでいるかどうかで評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（含む: 1.0, 含まない: 0.0）
        """
        return float(reference.strip() in hypothesis.strip())
