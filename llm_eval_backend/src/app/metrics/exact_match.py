"""
完全一致評価指標モジュール
"""
from typing import Dict, Any, Optional
from .base import BaseMetric, register_metric, ParamDef


@register_metric
class ExactMatch(BaseMetric):
    """
    完全一致評価指標
    
    空白や大小文字を無視するオプションを持つ
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ
        """
        super().__init__(name="exact_match", parameters=parameters)
        self.is_higher_better = True  # 値が高いほど良い

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        完全一致評価指標で使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "ignore_case": {
                "type": "boolean",
                "description": "大文字・小文字を区別しない",
                "default": False,
                "required": False
            },
            "ignore_whitespace": {
                "type": "boolean",
                "description": "空白文字を無視する（前後のみではなく全ての空白）",
                "default": False,
                "required": False
            }
        }

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        完全一致で評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（一致: 1.0, 不一致: 0.0）
        """
        # パラメータを取得
        ignore_case = self.parameters.get("ignore_case", False)
        ignore_whitespace = self.parameters.get("ignore_whitespace", False)
        
        # 前後の空白は常に削除
        hyp = hypothesis.strip()
        ref = reference.strip()
        
        # 設定に応じて追加処理
        if ignore_case:
            hyp = hyp.lower()
            ref = ref.lower()
            
        if ignore_whitespace:
            import re
            hyp = re.sub(r'\s+', '', hyp)
            ref = re.sub(r'\s+', '', ref)
        
        return float(hyp == ref)
