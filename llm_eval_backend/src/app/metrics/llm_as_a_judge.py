"""
LLMを使用して回答品質の評価を行うメトリクスモジュール
"""

from typing import Dict, Any, Optional, Union, List
from app.metrics.base import BaseMetric, register_metric, ParamDef
from litellm import completion
import re
import logging
from app.utils.db.providers import get_api_key_by_provider_name

logger = logging.getLogger(__name__)

# システムプロンプト（カテゴリ別）
SYSTEM_PROMPTS = {
    # 一般的なタスク用のシングル評価プロンプト
    "default": """Please act as an impartial judge and evaluate the quality of the response provided by an AI assistant to the user question displayed below. Your evaluation should consider factors such as the helpfulness, relevance, accuracy, depth, creativity, and level of detail of the response. Begin your evaluation by providing a short explanation. Be as objective as possible. The expected language is Japanese. Responses in languages other than Japanese will incur score deductions unless specifically required. Failure to use Japanese at all will result in the lowest evaluation. However, using Japanese is not mandatory when providing only Python scripts or calculation results, where Japanese is not essential. Additionally, your explanation of judgement should be in Japanese. After providing your explanation, you must rate the response on a scale of 1 to 10 by strictly following this format: "[[rating]]", for example: "Rating: [[5]]".""",
    
    # 数学・推論タスク用のシングル評価プロンプト
    "math": """Please act as an impartial judge and evaluate the quality of the response provided by an AI assistant to the math or reasoning question displayed below. Your evaluation should consider the correctness of the solution, the clarity of the explanation, and the appropriateness of the approach. Identify any errors in calculation, methodology, or reasoning. If the response contains a correct solution but lacks clarity, it should receive a lower rating than a correct, well-explained solution. Begin your evaluation by providing a short explanation and note any errors. The expected language is Japanese, unless specifically required for the calculation. After providing your explanation, you must rate the response on a scale of 1 to 10 by strictly following this format: "[[rating]]", for example: "Rating: [[5]]".""",
    
    # コーディングタスク用のシングル評価プロンプト
    "coding": """Please act as an impartial judge and evaluate the quality of the coding response provided by an AI assistant to the programming question displayed below. Your evaluation should consider the correctness, efficiency, clarity, and style of the code, as well as the quality of the explanation. Identify any bugs, edge cases not handled, inefficient implementations, or poor coding practices. Begin your evaluation by providing a short explanation and note any issues with the code or explanation. The expected language is Japanese, but English variable names and code comments are acceptable. After providing your explanation, you must rate the response on a scale of 1 to 10 by strictly following this format: "[[rating]]", for example: "Rating: [[5]]"."""
}

# マルチターンタスク用のシステムプロンプト
MULTI_TURN_DEFAULT_SYSTEM_PROMPT = """Please act as an impartial judge and evaluate the quality of the response provided by an AI assistant to the user question displayed below. Your evaluation should consider factors such as the helpfulness, relevance, accuracy, depth, creativity, and level of detail of the response. You evaluation should focus on the assistant's answer to the second user question. Begin your evaluation by providing a short explanation. Be as objective as possible. The expected language is Japanese. Responses in languages other than Japanese will incur score deductions unless specifically required. Failure to use Japanese at all will result in the lowest evaluation. However, using Japanese is not mandatory when providing only Python scripts or calculation results, where Japanese is not essential. Additionally, your explanation of judgement should be in Japanese. After providing your explanation, you must rate the response on a scale of 1 to 10 by strictly following this format: "[[rating]]", for example: "Rating: [[5]]"."""

# 評価スコアを抽出するための正規表現パターン
RATING_PATTERN = re.compile(r"\[\[(\d+(?:\.\d+)?)\]\]")
RATING_PATTERN_BACKUP = re.compile(r"\[(\d+(?:\.\d+)?)\]")

# MT-Benchで必要な参照回答が必要なカテゴリー
NEED_REF_CATS = ["math", "reasoning", "coding", "stem"]

def build_multi_turn_prompt_template(turns: int, with_reference: bool = False) -> str:
    """
    指定されたターン数に対応するマルチターン評価用テンプレートを構築します。

    Args:
        turns (int): 質問と回答のペア数（ターン数）
        with_reference (bool): 参照回答を含めるかどうか

    Returns:
        str: プレースホルダ付きテンプレート文字列

    Example:
        >>> template = build_multi_turn_prompt_template(2, with_reference=True)
        >>> print(template)
        <|The Start of Reference Answer|>\n
        ### User:\n{question_1}\n
        ### Reference answer:\n{reference_1}\n
        ### User:\n{question_2}\n
        ### Reference answer:\n{reference_2}\n
        <|The End of Reference Answer|>\n
        <|The Start of Assistant A's Conversation with User|>\n
        ### User:\n{question_1}\n
        ### Assistant A:\n{hypothesis_1}\n
        ### User:\n{question_2}\n
        ### Assistant A:\n{hypothesis_2}\n
        <|The End of Assistant A's Conversation with User|>
    """
    lines = []

    if with_reference:
        lines.append("<|The Start of Reference Answer|>\n")
        for i in range(1, turns + 1):
            lines.append(f"### User:\n{{question_{i}}}\n")
            lines.append(f"### Reference answer:\n{{reference_{i}}}\n")
        lines.append("<|The End of Reference Answer|>\n\n")

    lines.append("<|The Start of Assistant A's Conversation with User|>\n")
    for i in range(1, turns + 1):
        lines.append(f"### User:\n{{question_{i}}}\n")
        lines.append(f"### Assistant A:\n{{hypothesis_{i}}}\n")
    lines.append("<|The End of Assistant A's Conversation with User|>")

    return "\n".join(lines)



@register_metric
class LlmJudge(BaseMetric):
    """
    LLMを用いてAI応答の品質を1から10のスケールで評価し、0から1に正規化する評価指標クラスです。

    Attributes:
        is_higher_better (bool): 値が大きいほど良い評価かどうか
        parameters (dict): 評価時のパラメータ設定

    Example:
        >>> params = {'judge_model': 'gpt-4o-2024-05-13', 'judge_provider': 'openai'}
        >>> judge = LlmJudge(parameters=params)
        >>> score = judge.calculate(
        ...     hypothesis="応答文",
        ...     reference="参照文",
        ...     question="ユーザーの質問"
        ... )
        >>> print(f"正規化スコア: {score:.2f}")
    """
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters (Optional[Dict[str, Any]]): 評価指標のパラメータ
        """
        super().__init__(name="llm_as_a_judge", parameters=parameters)
        self.is_higher_better = True
        self.parameters = parameters if parameters else {}

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        この評価指標がサポートするパラメータ定義を返します。
        
        Returns:
            ParamDef: パラメータ名とメタ情報の辞書
        """
        return {
            "judge_model": {
                "type": "string",
                "description": "評価に使用するLLMモデル",
                "default": "gpt-4o-2024-05-13",
                "required": False
            },
            "judge_provider": {
                "type": "string",
                "description": "評価に使用するプロバイダ",
                "default": "openai",
                "required": False
            },
            "api_key": {
                "type": "string",
                "description": "LLMプロバイダーのAPIキー（設定されていない場合は環境変数から取得）",
                "default": "",
                "required": False
            },
            "max_tokens": {
                "type": "number",
                "description": "最大トークン数",
                "default": 2048,
                "required": False
            },
            "task_category": {
                "type": "string",
                "description": "タスクのカテゴリ（math, reasoning, coding, writing, roleplay, extraction, stemなど）",
                "default": "general",
                "enum": ["general", "math", "reasoning", "coding", "writing", "roleplay", "extraction", "stem", "humanities"],
                "required": False
            },
            "multi_turn": {
                "type": "boolean",
                "description": "マルチターン評価を実行するかどうか",
                "default": True,
                "required": False
            },
            "turn_to_evaluate": {
                "type": "number",
                "description": "評価する特定のターン番号（1から始まる）。指定しない場合は最終ターンを評価します。",
                "default": 0,
                "required": False
            }
        }

    def _extract_score(self, judgment: str) -> float:
        """
        LLMの評価レスポンスからスコアを抽出します。

        Args:
            judgment (str): LLMから返された評価レスポンス文字列

        Returns:
            float: 抽出されたスコア（0〜10）

        Example:
            >>> raw = "とても良い回答です。[[7.5]]"
            >>> score = LlmJudge()._extract_score(raw)
            >>> print(score)
            7.5
        """
        # 単一スコアを抽出
        match = RATING_PATTERN.search(judgment)
        if not match:
            # バックアップパターンで試行
            match = RATING_PATTERN_BACKUP.search(judgment)
            if not match:
                logger.warning(f"スコアが見つかりませんでした: {judgment}")
                return 0.0
        
        try:
            score = float(match.group(1))
            # スコアの範囲を確認
            if score < 0:
                score = 0.0
            if score > 10:
                score = 10.0
                
            return score
        except (ValueError, IndexError):
            logger.warning(f"スコアの解析に失敗しました: {match.group(0)}")
            return 0.0

    def _select_system_prompt(self, category: str) -> str:
        """
        カテゴリに基づいて適切なシステムプロンプトを選択します。

        Args:
            category (str): タスクカテゴリ

        Returns:
            str: 選択されたシステムプロンプト
        """
        # カテゴリを小文字化
        category = category.lower()
        
        # 数学/推論関連のカテゴリ
        if category in ["math", "reasoning", "stem"]:
            return SYSTEM_PROMPTS["math"]
        # コーディング関連のカテゴリ
        elif category in ["coding"]:
            return SYSTEM_PROMPTS["coding"]
        # デフォルト
        else:
            return SYSTEM_PROMPTS["default"]

    def calculate(self, hypothesis: Union[str, List[str]], reference: Union[str, List[str]], **kwargs) -> float:
        """
        LLMを呼び出して応答を評価し、スコアを0〜1に正規化して返します。

        Args:
            hypothesis (str | List[str]): AIの応答文または応答文のリスト
            reference (str | List[str]): 正解文または正解文のリスト
            question (str | List[str]): ユーザーからの質問文またはそのリスト
            category (str, optional): タスクカテゴリ

        Returns:
            float: 正規化後評価スコア（0〜1）

        Raises:
            ValueError: `question` 引数が提供されていない場合、またはhypothesis/referenceの長さ不一致時

        Example:
            >>> judge = LlmJudge()
            >>> score = judge.calculate(
            ...     hypothesis="こんにちは",
            ...     reference="こんにちは",
            ...     question="挨拶をしてください"
            ... )
            >>> print(score)
            1.0
        """
        question = kwargs.get("question")
        if question is None:
            raise ValueError("評価には 'question' 引数が必要です。")

        # カテゴリ情報の取得（パラメータかkwargsから）
        category = kwargs.get("category", self.parameters.get("task_category", "general"))
        
        # hypothesisとreferenceがstr型の場合はリストに変換
        if isinstance(hypothesis, str):
            hypothesis = [hypothesis]
        if isinstance(reference, str):
            reference = [reference]
        if isinstance(question, str):
            question = [question]
        
        # hypothesisとreferenceの長さを確認
        if len(hypothesis) != len(reference):
            raise ValueError("hypothesisとreferenceのリストは同じ長さでなければなりません。")

        # 評価するターン番号を決定（0ならば最終ターン）
        turn_to_evaluate = int(self.parameters.get("turn_to_evaluate", 0))
        if turn_to_evaluate <= 0:
            turn_to_evaluate = len(hypothesis)  # 最終ターン
        elif turn_to_evaluate > len(hypothesis):
            turn_to_evaluate = len(hypothesis)  # 範囲外なら最終ターン
        
        # 多数のターンがあるが単一ターンだけを評価したい場合の処理
        is_multi_turn = self.parameters.get("multi_turn", True) and len(hypothesis) > 1
        
        # 適切なシステムプロンプトを選択
        if is_multi_turn:
            system_prompt = MULTI_TURN_DEFAULT_SYSTEM_PROMPT
        else:
            system_prompt = self._select_system_prompt(category)
        
        # メッセージの準備
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # promptの生成
        # もしreferenceの要素0が空であれば、referenceは使用しない
        if reference[0] == "" or all(ref == "" for ref in reference):
            with_reference = False
        else:
            with_reference = True
            # 参照回答が必要なカテゴリかどうかを確認
            if not any(cat in category.lower() for cat in NEED_REF_CATS):
                with_reference = False  # 必要ないカテゴリでは参照回答を使わない
                
        prompt_template = build_multi_turn_prompt_template(len(hypothesis), with_reference=with_reference)

        # プレースホルダに埋め込む辞書を作成
        format_dict = {}
        for i in range(len(hypothesis)):
            format_dict[f"question_{i+1}"] = question[i]
            format_dict[f"hypothesis_{i+1}"] = hypothesis[i]
            format_dict[f"reference_{i+1}"] = reference[i] if i < len(reference) else ""

        # テンプレートに値を埋め込む
        prompt = prompt_template.format(**format_dict)

        # メッセージに追加
        messages.append({"role": "user", "content": prompt})

        # パラメータの取得
        judge_model = self.parameters.get("judge_model", "gpt-4o-2024-05-13")
        judge_provider = self.parameters.get("judge_provider", "openai")
        api_key = self.parameters.get("api_key", "")   
        max_tokens = self.parameters.get("max_tokens", 2048)

        # APIキーの取得
        if not api_key:
            api_key = get_api_key_by_provider_name(judge_provider)
            
        logger.info(f"LLM評価を実行: モデル={judge_model}, プロバイダ={judge_provider}, カテゴリ={category}, マルチターン={is_multi_turn}")
        logger.info(f"評価対象ターン: {turn_to_evaluate}/{len(hypothesis)}")

        # 推論の実行
        try:
            completion_response = completion(
                model=judge_model,
                messages=messages,
                api_key=api_key,
                max_tokens=max_tokens
            )

            # レスポンス本文を取り出す
            response_text = completion_response.choices[0].message.content
            logger.info(f"評価結果: {response_text[:100]}...")

            # スコアを抽出
            score = self._extract_score(response_text)        
            score = score / 10.0
            
            logger.info(f"抽出スコア: {score:.3f} (正規化後)")
            return score
            
        except Exception as e:
            logger.error(f"LLM評価実行中にエラーが発生しました: {e}")
            return 0.0