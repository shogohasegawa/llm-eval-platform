"""
BLEUスコア評価指標モジュール
"""
from .base import BaseMetric, register_metric


@register_metric
class BLEUScore(BaseMetric):
    """
    BLEUスコア評価指標
    """

    def __init__(self, parameters=None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="bleu", parameters=parameters)
        try:
            from sacrebleu import BLEU
            self.bleu = BLEU()
        except ImportError:
            raise ImportError("sacrebleu is required for BLEUScore metric")

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        BLEUスコアで評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（0.0-1.0）
        """
        return self.bleu.sentence_score(hypothesis.strip(), [reference.strip()]).score / 100.0
