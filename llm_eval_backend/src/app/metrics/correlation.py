"""
相関係数評価指標モジュール
"""
import math
import re
from typing import Dict, Any, Optional
from scipy.stats import pearsonr, spearmanr
from .base import BaseMetric, register_metric, ParamDef


def parse_float(input_str: str) -> float:
    """
    文字列から浮動小数点数を抽出する関数
    
    Args:
        input_str: 入力文字列
        
    Returns:
        float: 抽出された浮動小数点数、失敗した場合は-2.0
    """
    input_str = str(input_str)
    cleaned_str = re.sub(r"[^0-9.]", "", input_str)
    try:
        return float(cleaned_str)
    except ValueError:
        return -2.0


@register_metric
class PearsonCorrelation(BaseMetric):
    """
    ピアソン相関係数評価指標
    
    数値データの線形相関を評価するためのメトリクス
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="pearson", parameters=parameters)
        self.is_higher_better = True

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        ピアソン相関係数で評価する
        
        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力
            
        Returns:
            float: 評価スコア（-1.0-1.0）
        """
        try:
            # 文字列から数値を抽出
            y_pred = parse_float(hypothesis.strip())
            y_true = float(reference.strip())
            
            # 単一値の場合はリストに変換
            pearson = pearsonr([y_true], [y_pred])[0]
            
            # NaNの場合は0を返す
            if math.isnan(pearson):
                return 0.0
                
            return pearson
        except Exception as e:
            print(f"ピアソン相関係数の計算中にエラーが発生しました: {e}")
            return 0.0


@register_metric
class SpearmanCorrelation(BaseMetric):
    """
    スピアマン相関係数評価指標
    
    数値データの順位相関を評価するためのメトリクス
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="spearman", parameters=parameters)
        self.is_higher_better = True

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        スピアマン相関係数で評価する
        
        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力
            
        Returns:
            float: 評価スコア（-1.0-1.0）
        """
        try:
            # 文字列から数値を抽出
            y_pred = parse_float(hypothesis.strip())
            y_true = float(reference.strip())
            
            # 単一値の場合はリストに変換
            spearman = spearmanr([y_true], [y_pred])[0]
            
            # NaNの場合は0を返す
            if math.isnan(spearman):
                return 0.0
                
            return spearman
        except Exception as e:
            print(f"スピアマン相関係数の計算中にエラーが発生しました: {e}")
            return 0.0