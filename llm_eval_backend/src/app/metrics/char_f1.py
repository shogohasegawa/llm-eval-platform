"""
文字ベースのF1スコア評価指標モジュール
"""
from typing import Dict, Any, Optional
from .base import BaseMetric, register_metric, ParamDef
from fuzzywuzzy import fuzz


@register_metric
class CharF1(BaseMetric):
    """
    文字ベースのF1スコア評価指標
    
    fuzzywuzzyライブラリを使用した文字ベースの類似度測定。
    Nejumiでは文字列をそのまま比較し、前処理を行わない実装を使用しています。
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="char_f1", parameters=parameters)
        self.is_higher_better = True

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        文字ベースのF1スコア評価指標で使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "strip_whitespace": {
                "type": "boolean",
                "description": "前後の空白を削除する",
                "default": False,
                "required": False
            },
            "nejumi_compatible": {
                "type": "boolean",
                "description": "Nejumi Leaderboardと同じ実装を使用する",
                "default": True,
                "required": False
            }
        }

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        文字ベースのF1スコアで評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（0.0-1.0）
        """
        # Nejumi互換モード
        if self.parameters.get("nejumi_compatible", True):
            # Nejumiと同じ実装
            return fuzz.token_sort_ratio(hypothesis, reference) / 100.0
        
        # 拡張モード
        strip_whitespace = self.parameters.get("strip_whitespace", False)
        
        # オプションで前後の空白を削除
        hyp = hypothesis.strip() if strip_whitespace else hypothesis
        ref = reference.strip() if strip_whitespace else reference
        
        return fuzz.token_sort_ratio(hyp, ref) / 100.0