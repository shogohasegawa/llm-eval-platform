"""
新しく追加された評価メトリクスのテスト
"""
import pytest
from app.metrics.bleu import BLEUScore
from app.metrics.correlation import PearsonCorrelation, SpearmanCorrelation

# bert_scoreとcometはオプショナルな依存関係のため、インポートできない場合はスキップ
try:
    from app.metrics.bert_score import BERTScore
    BERTSCORE_AVAILABLE = True
except ImportError:
    BERTSCORE_AVAILABLE = False

try:
    from app.metrics.comet import COMETScore
    COMET_AVAILABLE = True
except ImportError:
    COMET_AVAILABLE = False


def test_bleu_with_language():
    """
    言語設定付きBLEUスコアメトリクスのテスト
    """
    # 日本語設定でのテスト
    ja_metric = BLEUScore(parameters={"language": "ja"})
    
    # 完全一致
    assert ja_metric.calculate("これはテストです。", "これはテストです。") == 1.0
    
    # 部分一致
    assert 0 < ja_metric.calculate("これはテストです。", "これはテストだ。") < 1.0
    
    # 英語設定でのテスト
    en_metric = BLEUScore(parameters={"language": "en"})
    
    # 完全一致
    assert en_metric.calculate("This is a test.", "This is a test.") == 1.0
    
    # 部分一致
    assert 0 < en_metric.calculate("This is a test.", "This is testing.") < 1.0
    
    # 空入力
    assert ja_metric.calculate("", "") == 1.0
    assert ja_metric.calculate("テスト", "") == 0.0


def test_pearson_correlation():
    """
    ピアソン相関係数メトリクスのテスト
    """
    metric = PearsonCorrelation()
    
    # 同一値の場合は1.0（ただし単一値の場合は特殊処理）
    assert abs(metric.calculate("5.0", "5.0") - 1.0) < 0.001
    
    # 数値が抽出できない場合は0.0
    assert metric.calculate("非数値", "5.0") == 0.0
    
    # 空入力
    assert metric.calculate("", "") == 0.0


def test_spearman_correlation():
    """
    スピアマン相関係数メトリクスのテスト
    """
    metric = SpearmanCorrelation()
    
    # 同一値の場合は1.0（ただし単一値の場合は特殊処理）
    assert abs(metric.calculate("5.0", "5.0") - 1.0) < 0.001
    
    # 数値が抽出できない場合は0.0
    assert metric.calculate("非数値", "5.0") == 0.0
    
    # 空入力
    assert metric.calculate("", "") == 0.0


@pytest.mark.skipif(not BERTSCORE_AVAILABLE, reason="bert-score not installed")
def test_bert_score():
    """
    BERTScoreメトリクスのテスト
    """
    # bert-scoreの依存関係がインストールされている場合のみテスト
    metric = BERTScore()
    
    # 完全一致に近い値を期待（実際の値はモデルに依存）
    # このテストは依存関係がある場合のみ実行する
    assert metric.calculate("これはテストです。", "これはテストです。") > 0.8
    
    # 空入力
    assert metric.calculate("", "") == 1.0
    assert metric.calculate("テスト", "") == 0.0


@pytest.mark.skipif(not COMET_AVAILABLE, reason="unbabel-comet not installed")
def test_comet_score():
    """
    COMETスコアメトリクスのテスト
    """
    # cometの依存関係がインストールされている場合のみテスト
    # このテストはパラメータに依存するため、モック化が必要
    pass