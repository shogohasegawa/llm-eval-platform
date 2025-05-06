"""
BLEUスコア評価指標モジュール
"""
from typing import Dict, Any, Optional
from .base import BaseMetric, register_metric, ParamDef


@register_metric
class BLEUScore(BaseMetric):
    """
    BLEUスコア評価指標
    
    機械翻訳や生成文の評価のために広く使われるメトリクス。
    n-gramの一致に基づいて計算される。
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="bleu", parameters=parameters)
        self.is_higher_better = True
        try:
            from sacrebleu import BLEU
            self.BLEU = BLEU
        except ImportError:
            raise ImportError("sacrebleu is required for BLEUScore metric")

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        BLEUスコア評価指標で使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "language": {
                "type": "string",
                "description": "評価する言語（ja: 日本語, en: 英語）",
                "default": "ja",
                "enum": ["ja", "en", "auto"],
                "required": False
            },
            "effective_order": {
                "type": "boolean",
                "description": "実効的なn-gramの順序を使用",
                "default": True,
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
        BLEUスコアで評価する

        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力

        Returns:
            float: 評価スコア（0.0-1.0）
        """
        # 入力の前処理
        hypothesis = hypothesis.strip()
        reference = reference.strip()
        
        # 空の入力チェック
        if not reference:
            raise ValueError("The reference text is empty.")
        if not hypothesis:
            return 0.0
        
        # パラメータの取得
        language = self.parameters.get("language", "ja")
        effective_order = self.parameters.get("effective_order", True)
        nejumi_compatible = self.parameters.get("nejumi_compatible", True)
        
        # BLEUの設定
        bleu_config = {
            "effective_order": effective_order,
        }
        
        # 言語が指定されている場合は設定
        if language != "auto":
            bleu_config["trg_lang"] = language
            
        # BLEUインスタンスを作成
        bleu = self.BLEU(**bleu_config)
        
        # スコアを計算
        try:
            bleu_score = bleu.corpus_score([hypothesis], [[reference]]).score
            return bleu_score / 100.0
        except Exception as e:
            if nejumi_compatible:
                # Nejumiでは例外を投げずに0.0を返すケースがある
                print(f"BLEUスコア計算中にエラーが発生しました: {e}")
                return 0.0
            else:
                # 拡張モードでは例外を伝播
                raise