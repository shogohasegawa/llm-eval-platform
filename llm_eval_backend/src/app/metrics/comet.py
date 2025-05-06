"""
COMETスコア評価指標モジュール

機械翻訳の品質評価のためのニューラルメトリクス
"""
from typing import Dict, Any, Optional
from .base import BaseMetric, register_metric, ParamDef


@register_metric
class COMETScore(BaseMetric):
    """
    COMETスコア評価指標
    
    Crosslingual Optimized Metric for Evaluation of Translation（COMET）
    機械翻訳の品質評価に特化したニューラルメトリクス
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ (オプション)
        """
        super().__init__(name="comet", parameters=parameters)
        self.is_higher_better = True
        self.model = None
        self.model_path = None
        
        try:
            from comet import download_model, load_from_checkpoint
            self.download_model = download_model
            self.load_from_checkpoint = load_from_checkpoint
        except ImportError:
            raise ImportError("unbabel-comet is required for COMETScore metric. " 
                              "Please install it with: pip install unbabel-comet")

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        COMETスコア評価指標で使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "model_name": {
                "type": "string",
                "description": "使用するCOMETモデル名",
                "default": "Unbabel/wmt22-comet-da",
                "required": False
            },
            "source_text": {
                "type": "string",
                "description": "翻訳元のテキスト（必須）",
                "required": True
            }
        }

    def _load_model(self, model_name: str):
        """
        COMETモデルを読み込む内部メソッド
        
        Args:
            model_name: モデル名
        """
        if self.model is None or self.model_path != model_name:
            self.model_path = self.download_model(model_name)
            self.model = self.load_from_checkpoint(self.model_path)

    def calculate(self, hypothesis: str, reference: str) -> float:
        """
        COMETスコアで評価する
        
        Args:
            hypothesis: モデルの翻訳出力
            reference: 正解翻訳
            
        Returns:
            float: 評価スコア
        """
        # source_textパラメータが必須
        if "source_text" not in self.parameters:
            raise ValueError("COMETスコアの計算にはsource_textパラメータが必要です")
            
        source_text = self.parameters.get("source_text")
        model_name = self.parameters.get("model_name", "Unbabel/wmt22-comet-da")
        
        # 空入力のチェック
        if not hypothesis.strip() or not reference.strip() or not source_text.strip():
            return 0.0
            
        try:
            # モデルの読み込み
            self._load_model(model_name)
            
            # 評価データの作成
            comet_data = [{
                "src": source_text,
                "mt": hypothesis,
                "ref": reference
            }]
            
            # スコアの計算
            result = self.model.predict(comet_data, batch_size=1, gpus=0)
            score = result.scores[0]
            
            return score
            
        except Exception as e:
            print(f"COMETスコア計算中にエラーが発生しました: {e}")
            return 0.0