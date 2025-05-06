"""
BERTScoreモジュール

文章の意味的類似性を測定するためのメトリクス
"""
from typing import Dict, Any, Optional
from .base import BaseMetric, register_metric, ParamDef


@register_metric
class BERTScore(BaseMetric):
    """
    BERTScoreメトリクス
    
    事前学習済み言語モデルの埋め込みを使用して、
    文章間の意味的類似性を測定するメトリクス
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="bert_score", parameters=parameters)
        self.is_higher_better = True
        
        try:
            import bert_score
            self.bert_score = bert_score
        except ImportError:
            raise ImportError("bert-score is required for BERTScore metric. " 
                              "Please install it with: pip install bert-score")

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        BERTScoreで使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "lang": {
                "type": "string",
                "description": "使用する言語（ja: 日本語, en: 英語）",
                "default": "ja",
                "enum": ["ja", "en"],
                "required": False
            },
            "score_type": {
                "type": "string",
                "description": "スコアの種類（P: 適合率, R: 再現率, F1: F1スコア）",
                "default": "F1",
                "enum": ["P", "R", "F1"],
                "required": False
            }
        }

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        BERTScoreで評価する
        
        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力
            
        Returns:
            float: 評価スコア（0.0-1.0）
        """
        # 空入力のチェック
        if not hypothesis.strip() or not reference.strip():
            return 0.0 if hypothesis.strip() != reference.strip() else 1.0
            
        # パラメータの取得
        lang = self.parameters.get("lang", "ja")
        score_type = self.parameters.get("score_type", "F1")
        
        try:
            # BERTScoreの計算
            # P（適合率）, R（再現率）, F1（F値）の順に結果が返される
            P, R, F1 = self.bert_score.score([hypothesis], [reference], lang=lang)
            
            # スコアタイプに応じた値を返す
            if score_type == "P":
                return P.item()
            elif score_type == "R":
                return R.item()
            else:  # デフォルトはF1
                return F1.item()
                
        except Exception as e:
            print(f"BERTScore計算中にエラーが発生しました: {e}")
            return 0.0