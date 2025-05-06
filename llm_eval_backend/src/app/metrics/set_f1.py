"""
集合ベースのF1スコア評価指標モジュール
"""
from typing import Dict, Any, Optional
from .base import BaseMetric, register_metric, ParamDef


@register_metric
class SetF1(BaseMetric):
    """
    集合ベースのF1スコア評価指標
    
    改行で区切られた項目リストをセットとして扱い、F1スコアを計算します。
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド

        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="set_f1", parameters=parameters)
        self.is_higher_better = True
        
    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        集合ベースのF1スコア評価指標で使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "delimiter": {
                "type": "string",
                "description": "項目の区切り文字",
                "default": "\n",
                "required": False
            },
            "nejumi_compatible": {
                "type": "boolean",
                "description": "Nejumi Leaderboardと同じ実装を使用するかどうか",
                "default": True,
                "required": False
            }
        }

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        集合ベースのF1スコアで評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（0.0-1.0）
        """
        # パラメータを取得
        delimiter = self.parameters.get("delimiter", "\n")
        nejumi_compatible = self.parameters.get("nejumi_compatible", True)
        
        if nejumi_compatible:
            # Nejumi実装に準拠
            set_y_true = [x.strip() for x in reference.split(delimiter) if x.strip()]
            set_y_pred = list({x.strip() for x in hypothesis.split(delimiter) if x.strip()})
            
            if not set_y_pred and not set_y_true:
                return 1.0
            if not set_y_pred or not set_y_true:
                return 0.0
            
            # Nejumiと同じ実装（注: 再現率の計算がNejumiでは特殊）
            set_pre = sum([1 if y in set_y_true else 0 for y in set_y_pred]) / len(set_y_pred)
            set_rec = sum([1 if y in set_y_true else 0 for y in set_y_pred]) / len(set_y_true)
            
            if set_pre + set_rec == 0:
                return 0.0
            
            set_f1 = 2 * (set_pre * set_rec) / (set_pre + set_rec)
            return set_f1
        else:
            # オリジナル実装
            set_pred = {x.strip() for x in hypothesis.split(delimiter) if x.strip()}
            set_ref = {x.strip() for x in reference.split(delimiter) if x.strip()}

            if not set_pred and not set_ref:
                return 1.0
            if not set_pred or not set_ref:
                return 0.0

            true_positives = len(set_pred.intersection(set_ref))
            precision = true_positives / len(set_pred)
            recall = true_positives / len(set_ref)

            if precision + recall == 0:
                return 0.0

            f1 = 2 * precision * recall / (precision + recall)
            return f1