"""
LLM Judgeメトリクスのテスト
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.metrics.llm_judge import LLMJudge


@pytest.fixture
def mock_litellm_response():
    """LiteLLMのレスポンスをモックするフィクスチャ"""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message = MagicMock()
    mock_resp.choices[0].message.content = """
    評価：
    この回答は質問に対して適切な情報を提供しています。回答は簡潔で分かりやすく、日本の首都が東京であるという事実を正確に述べています。
    
    Rating: [[8]]
    """
    return mock_resp

@pytest.fixture
def mock_litellm_pairwise_response():
    """LiteLLMのペアワイズレスポンスをモックするフィクスチャ"""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message = MagicMock()
    mock_resp.choices[0].message.content = """
    評価：
    
    回答Aと回答Bを比較しました。
    
    回答Aは簡潔かつ正確に日本の首都が東京であることを述べており、質問に直接答えています。
    
    回答Bはより詳細で、東京が政治・経済の中心であることにも触れていますが、少し冗長です。
    
    全体的に、両方の回答は正確ですが、回答Aの方がより簡潔です。
    
    スコア: [[8, 7]]
    """
    return mock_resp


@pytest.fixture
def llm_judge_metric():
    """LLMJudgeメトリクスのインスタンスを作成"""
    return LLMJudge(parameters={
        "judge_model": "gpt-4",
        "judge_provider": "openai",
        "system_prompt": "テスト用システムプロンプト",
        "prompt_template": "テスト用プロンプトテンプレート",
        "max_tokens": 100,
        "temperature": 0.1
    })

@pytest.fixture
def llm_judge_pairwise():
    """ペアワイズモードのLLMJudgeメトリクスのインスタンスを作成"""
    return LLMJudge(parameters={
        "judge_model": "gpt-4",
        "judge_provider": "openai",
        "system_prompt": "テスト用ペアワイズシステムプロンプト",
        "prompt_template": "テスト用ペアワイズプロンプトテンプレート",
        "max_tokens": 100,
        "temperature": 0.1,
        "mode": "pairwise"
    })

@pytest.fixture
def llm_judge_nejumi():
    """Nejumi互換モードのLLMJudgeメトリクスのインスタンスを作成"""
    return LLMJudge(parameters={
        "judge_model": "gpt-4",
        "judge_provider": "openai",
        "use_nejumi_prompts": True,
        "task_category": "general",
        "max_tokens": 100
    })


@patch('app.metrics.llm_judge.LLMJudge._call_llm')
def test_extract_score_single(mock_call_llm, llm_judge_metric):
    """シングルモードでのスコア抽出のテスト"""
    # 様々な形式のレスポンスに対するテスト
    examples = [
        ("評価：\n\nRating: [[8]]", 8.0),
        ("評価内容...\n\n[[7.5]]", 7.5),
        ("詳細な評価...\n\nスコア: [9]", 9.0),  # バックアップパターン
        ("評価がスコア形式でない場合", 0.0),  # スコアがない場合
        ("評価：\n\nRating: [[11]]", 10.0),  # 範囲外（上限）
        ("評価：\n\nRating: [[-1]]", 0.0),   # 範囲外（下限）
    ]
    
    for judgment, expected in examples:
        score = llm_judge_metric._extract_score(judgment)
        assert score == expected

@patch('app.metrics.llm_judge.LLMJudge._call_llm')
def test_extract_score_pairwise(mock_call_llm, llm_judge_pairwise):
    """ペアワイズモードでのスコア抽出のテスト"""
    # 様々な形式のレスポンスに対するテスト
    examples = [
        ("評価：\n\nスコア: [[8, 7]]", (8.0, 7.0)),
        ("評価内容...\n\n[[7.5, 6.5]]", (7.5, 6.5)),
        ("詳細な評価...\n\nスコア: [9, 8]", (9.0, 8.0)),  # バックアップパターン
        ("評価がスコア形式でない場合", (0.0, 0.0)),  # スコアがない場合
        ("評価：\n\nRating: [[11, 9]]", (10.0, 9.0)),  # 範囲外（上限）
        ("評価：\n\nRating: [[-1, 0]]", (0.0, 0.0)),   # 範囲外（下限）
    ]
    
    for judgment, expected in examples:
        scores = llm_judge_pairwise._extract_score(judgment)
        assert scores == expected


@patch('app.metrics.llm_judge.LLMJudge.acompletion')
def test_call_llm(mock_acompletion, mock_litellm_response, llm_judge_metric):
    """LLM呼び出しのテスト"""
    mock_acompletion.return_value = mock_litellm_response
    
    # run_until_completeを使わないように非同期関数を直接テスト
    async def test():
        messages = [
            {"role": "system", "content": "テスト用システムプロンプト"},
            {"role": "user", "content": "テスト用ユーザープロンプト"}
        ]
        result = await llm_judge_metric._call_llm(messages)
        assert "Rating: [[8]]" in result
        mock_acompletion.assert_called_once()
    
    # 非同期テストを実行
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())


@patch('app.metrics.llm_judge.LLMJudge.acompletion')
def test_calculate_with_scaling(mock_acompletion, mock_litellm_response, llm_judge_metric):
    """スケーリングありのcalculateメソッドのテスト"""
    mock_acompletion.return_value = mock_litellm_response
    
    # スケーリングありの場合（デフォルト）
    score = llm_judge_metric.calculate(
        hypothesis="日本の首都は東京です。",
        reference="日本の首都はどこですか？"
    )
    assert score == 0.8  # 8.0 / 10.0


@patch('app.metrics.llm_judge.LLMJudge.acompletion')
def test_calculate_without_scaling(mock_acompletion, mock_litellm_response, llm_judge_metric):
    """スケーリングなしのcalculateメソッドのテスト"""
    mock_acompletion.return_value = mock_litellm_response
    
    # スケーリングなしのパラメータを設定
    llm_judge_metric.parameters["scale_to_range"] = False
    
    score = llm_judge_metric.calculate(
        hypothesis="日本の首都は東京です。",
        reference="日本の首都はどこですか？"
    )
    assert score == 8.0  # スケーリングなしの生のスコア


@patch('app.metrics.llm_judge.LLMJudge.acompletion')
def test_calculate_with_reference(mock_acompletion, mock_litellm_response, llm_judge_metric):
    """リファレンス使用のcalculateメソッドのテスト"""
    mock_acompletion.return_value = mock_litellm_response
    
    # リファレンス使用のパラメータを設定
    llm_judge_metric.parameters["use_reference"] = True
    
    score = llm_judge_metric.calculate(
        hypothesis="日本の首都は東京です。",
        reference="日本の首都はどこですか？"
    )
    assert score == 0.8  # 8.0 / 10.0
    # リファレンス使用のテンプレートが使われることを確認するにはもっと詳細なモックが必要

@patch('app.metrics.llm_judge.LLMJudge.acompletion')
def test_calculate_pairwise(mock_acompletion, mock_litellm_pairwise_response, llm_judge_pairwise):
    """ペアワイズモードのcalculateメソッドのテスト"""
    mock_acompletion.return_value = mock_litellm_pairwise_response
    
    # ペアワイズ評価
    score = llm_judge_pairwise.calculate(
        hypothesis="日本の首都は東京です。",
        reference="日本の首都はどこですか？",
        hypothesis_b="日本の首都は東京で、政治・経済の中心となっています。"
    )
    
    # スケーリングありの場合、Aの方が高いスコアなので1.0
    assert score == 1.0
    
    # スケーリングなしの場合は実際のスコア
    llm_judge_pairwise.parameters["scale_to_range"] = False
    score = llm_judge_pairwise.calculate(
        hypothesis="日本の首都は東京です。",
        reference="日本の首都はどこですか？",
        hypothesis_b="日本の首都は東京で、政治・経済の中心となっています。"
    )
    assert score == 8.0

@patch('app.metrics.llm_judge.LLMJudge.acompletion')
def test_calculate_pairwise_tie(mock_acompletion, llm_judge_pairwise):
    """ペアワイズモードの同点のテスト"""
    # 同点の場合をモック
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message = MagicMock()
    mock_resp.choices[0].message.content = "評価：\n\nスコア: [[7, 7]]"
    mock_acompletion.return_value = mock_resp
    
    # 同点の場合は0.5
    score = llm_judge_pairwise.calculate(
        hypothesis="日本の首都は東京です。",
        reference="日本の首都はどこですか？",
        hypothesis_b="東京は日本の首都です。"
    )
    assert score == 0.5

@patch('app.metrics.llm_judge.LLMJudge.acompletion')
def test_nejumi_compatibility(mock_acompletion, mock_litellm_response, llm_judge_nejumi):
    """Nejumi互換モードのテスト"""
    mock_acompletion.return_value = mock_litellm_response
    
    # Nejumi互換モードでの評価
    score = llm_judge_nejumi.calculate(
        hypothesis="日本の首都は東京です。",
        reference="日本の首都はどこですか？"
    )
    assert score == 0.8  # 8.0 / 10.0
    
    # カテゴリを「math」に変更して参照回答が自動的に使用されるか確認
    llm_judge_nejumi.parameters["task_category"] = "math"
    score = llm_judge_nejumi.calculate(
        hypothesis="x = 5",
        reference="方程式 2x + 3 = 13 を解きなさい。"
    )
    assert score == 0.8  # 8.0 / 10.0
    
    # 非同期版も同様に動作するか確認
    async def test_async():
        score = await llm_judge_nejumi.calculate_async(
            hypothesis="日本の首都は東京です。",
            reference="日本の首都はどこですか？"
        )
        assert score == 0.8
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_async())