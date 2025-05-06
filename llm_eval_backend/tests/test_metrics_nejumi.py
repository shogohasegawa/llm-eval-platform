"""
Nejumi互換モードでのメトリクステスト
"""
import pytest
from app.metrics.char_f1 import CharF1
from app.metrics.exact_match import ExactMatch
from app.metrics.exact_match_figure import ExactMatchFigure
from app.metrics.set_f1 import SetF1
from app.metrics.bleu import BLEUScore
from app.metrics.contains_answer import ContainsAnswer


def test_exact_match_nejumi_mode():
    """
    Nejumi互換モードでのExactMatchメトリクスのテスト
    """
    metric = ExactMatch(parameters={"nejumi_compatible": True})
    
    # 完全一致
    assert metric.calculate("これはテストです。", "これはテストです。") == 1.0
    
    # スペースや改行の違いを無視しない
    assert metric.calculate("これはテストです。", "これはテストです。\n") == 0.0
    assert metric.calculate("これはテストです。", " これはテストです。 ") == 0.0
    
    # 部分一致は不一致
    assert metric.calculate("これはテストです。", "これはテストだ。") == 0.0


def test_exact_match_figure_nejumi_mode():
    """
    Nejumi互換モードでのExactMatchFigureメトリクスのテスト
    """
    metric = ExactMatchFigure(parameters={"nejumi_compatible": True})
    
    # 数値の完全一致
    assert metric.calculate("123.0", "123") == 1.0
    assert metric.calculate("123", "123.0") == 1.0
    assert metric.calculate("123.45", "123.45") == 1.0
    
    # 数値に変換できない場合
    assert metric.calculate("これはテストです。", "123") == 0.0
    assert metric.calculate("123", "これはテスト") == 0.0


def test_char_f1_nejumi_mode():
    """
    Nejumi互換モードでのCharF1メトリクスのテスト
    """
    metric = CharF1(parameters={"nejumi_compatible": True})
    
    # 完全一致
    assert metric.calculate("これはテストです。", "これはテストです。") == 1.0
    
    # 前後の空白を削除しない
    assert metric.calculate(" これはテストです。 ", "これはテストです。") < 1.0
    
    # 部分一致
    assert 0 < metric.calculate("これはテストです。", "これはテストだ。") < 1.0


def test_set_f1_nejumi_mode():
    """
    Nejumi互換モードでのSetF1メトリクスのテスト
    """
    metric = SetF1(parameters={"nejumi_compatible": True})
    
    # 完全一致
    test_lines1 = "項目1\n項目2\n項目3"
    test_lines2 = "項目1\n項目2\n項目3"
    assert metric.calculate(test_lines1, test_lines2) == 1.0
    
    # 順序が異なる場合
    test_lines3 = "項目3\n項目1\n項目2"
    assert metric.calculate(test_lines3, test_lines2) == 1.0
    
    # 一部のみ一致
    test_lines4 = "項目1\n項目2\n項目X"
    assert 0 < metric.calculate(test_lines4, test_lines2) < 1.0
    
    # 重複がある場合はセットとして扱う
    test_lines5 = "項目1\n項目1\n項目2"
    test_lines6 = "項目1\n項目2\n項目2"
    score = metric.calculate(test_lines5, test_lines6)
    assert score == 1.0  # 重複が除去されるため


def test_bleu_nejumi_mode():
    """
    Nejumi互換モードでのBLEUスコアメトリクスのテスト
    """
    metric_ja = BLEUScore(parameters={"language": "ja", "nejumi_compatible": True})
    
    # 日本語での完全一致
    assert metric_ja.calculate("これはテストです。", "これはテストです。") == 1.0
    
    # 部分一致
    assert 0 < metric_ja.calculate("これはテストです。", "これはテストになります。") < 1.0
    
    # 英語モードでのテスト
    metric_en = BLEUScore(parameters={"language": "en", "nejumi_compatible": True})
    
    # 英語での完全一致
    assert metric_en.calculate("This is a test.", "This is a test.") == 1.0


def test_contains_answer():
    """
    ContainsAnswerメトリクスのテスト
    """
    metric = ContainsAnswer()
    
    # 含む場合
    assert metric.calculate("これはテストです。正解は42です。", "42") == 1.0
    
    # 含まない場合
    assert metric.calculate("これはテストです。", "答えは42") == 0.0
    
    # 大文字小文字の区別（デフォルトは区別する）
    assert metric.calculate("The answer is YES.", "yes") == 0.0
    
    # 大文字小文字を区別しない
    metric_case_insensitive = ContainsAnswer(parameters={"case_sensitive": False})
    assert metric_case_insensitive.calculate("The answer is YES.", "yes") == 1.0