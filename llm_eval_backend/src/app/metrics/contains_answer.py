"""
回答を含むかどうかの評価指標モジュール
"""
from typing import Dict, Any, Optional
from .base import BaseMetric, register_metric, ParamDef


@register_metric
class ContainsAnswer(BaseMetric):
    """
    回答を含むかどうかの評価指標
    
    モデルの出力が正解を含んでいるかどうかをチェックします。
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="contains_answer", parameters=parameters)
        self.is_higher_better = True

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        回答を含むかどうかの評価指標で使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "strip_whitespace": {
                "type": "boolean",
                "description": "前後の空白を削除する",
                "default": True,
                "required": False
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "大文字小文字を区別する",
                "default": True,
                "required": False
            }
        }

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        予測文字列が正解を含んでいるかどうかで評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（含む: 1.0, 含まない: 0.0）
        """
        # パラメータを取得
        strip_whitespace = self.parameters.get("strip_whitespace", True)
        case_sensitive = self.parameters.get("case_sensitive", True)
        
        # 前処理
        hyp = hypothesis.strip() if strip_whitespace else hypothesis
        ref = reference.strip() if strip_whitespace else reference
        
        # 大文字小文字を区別しない場合
        if not case_sensitive:
            hyp = hyp.lower()
            ref = ref.lower()
        
        # 含まれているかチェック
        return float(ref in hyp)