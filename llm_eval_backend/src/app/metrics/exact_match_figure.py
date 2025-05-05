"""
図表の完全一致評価指標モジュール

このメトリクスは図表・表に特化した完全一致評価指標です。
"""
from typing import Dict, Any, Optional
import re
from .base import BaseMetric, register_metric, ParamDef


@register_metric
class ExactMatchFigure(BaseMetric):
    """
    図表・表の完全一致評価指標
    
    図表・表のような構造化テキストを評価するために最適化された指標です。
    行・列区切り文字や空白、大小文字などを無視するオプションを持っています。
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ
        """
        super().__init__(name="exact_match_figure", parameters=parameters)
        self.is_higher_better = True  # 値が高いほど良い

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        図表完全一致評価指標で使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "ignore_case": {
                "type": "boolean",
                "description": "大文字・小文字を区別しない",
                "default": True,
                "required": False
            },
            "ignore_whitespace": {
                "type": "boolean",
                "description": "空白文字を無視する（前後のみではなく全ての空白）",
                "default": True,
                "required": False
            },
            "ignore_table_separators": {
                "type": "boolean",
                "description": "表の区切り文字（|, -, +など）の違いを無視する",
                "default": True,
                "required": False
            },
            "ignore_newlines": {
                "type": "boolean",
                "description": "改行の数や位置を無視する",
                "default": False,
                "required": False
            },
            "normalize_numbers": {
                "type": "boolean",
                "description": "数値の表記を統一する（1.0 → 1、1,000 → 1000）",
                "default": True,
                "required": False
            }
        }

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        図表・表を考慮した完全一致で評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（一致: 1.0, 不一致: 0.0）
        """
        # パラメータを取得
        ignore_case = self.parameters.get("ignore_case", True)
        ignore_whitespace = self.parameters.get("ignore_whitespace", True)
        ignore_table_separators = self.parameters.get("ignore_table_separators", True)
        ignore_newlines = self.parameters.get("ignore_newlines", False)
        normalize_numbers = self.parameters.get("normalize_numbers", True)
        
        # 前後の空白は常に削除
        hyp = hypothesis.strip()
        ref = reference.strip()
        
        # 設定に応じて追加処理
        if ignore_case:
            hyp = hyp.lower()
            ref = ref.lower()
        
        if normalize_numbers:
            # 数値を正規化: 1,000 -> 1000, 1.0 -> 1
            hyp = re.sub(r'(\d),(\d)', r'\1\2', hyp)  # カンマを削除
            ref = re.sub(r'(\d),(\d)', r'\1\2', ref)
            hyp = re.sub(r'(\d+)\.0+\b', r'\1', hyp)  # 小数点以下が0の場合は整数に
            ref = re.sub(r'(\d+)\.0+\b', r'\1', ref)
        
        if ignore_table_separators:
            # 表の区切り文字を削除または統一
            table_separators = r'[\|\+\-=]'
            hyp = re.sub(table_separators, '', hyp)
            ref = re.sub(table_separators, '', ref)
        
        if ignore_whitespace:
            hyp = re.sub(r'\s+', '', hyp)
            ref = re.sub(r'\s+', '', ref)
        elif ignore_newlines:  # ignore_whitespaceがTrueの場合は改行も含めて無視されるため
            hyp = re.sub(r'\n+', ' ', hyp)
            ref = re.sub(r'\n+', ' ', ref)
            # 連続する空白を1つにまとめる
            hyp = re.sub(r'\s+', ' ', hyp)
            ref = re.sub(r'\s+', ' ', ref)
        
        return float(hyp == ref)