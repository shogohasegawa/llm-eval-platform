"""
LLM as a judgeメトリクスモジュール

LLMを使って回答の質を評価するメトリクス。
GPT-4などの高性能モデルを使用して、生成された回答の質を評価します。
Nejumi Leaderboardとの互換性を持つ実装です。
"""
import re
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
import logging
from .base import BaseMetric, register_metric, ParamDef

logger = logging.getLogger(__name__)

# 評価スコアを抽出するための正規表現パターン
RATING_PATTERN = re.compile(r"\[\[(\d+(?:\.\d+)?)\]\]")
RATING_PATTERN_BACKUP = re.compile(r"\[(\d+(?:\.\d+)?)\]")

# ペアワイズモードで2つのスコアを抽出するためのパターン
TWO_SCORE_PATTERN = re.compile(r"\[\[(\d+\.?\d*),\s?(\d+\.?\d*)\]\]")
TWO_SCORE_PATTERN_BACKUP = re.compile(r"\[(\d+\.?\d*),\s?(\d+\.?\d*)\]")

# カテゴリごとの生成温度設定
TEMPERATURE_CONFIG = {
    "writing": 0.7,
    "roleplay": 0.7,
    "extraction": 0.0,
    "math": 0.0,
    "coding": 0.0,
    "reasoning": 0.0,
    "stem": 0.1,
    "humanities": 0.1,
    "general": 0.1,  # デフォルト
}

# リファレンス回答が必要なカテゴリ
NEED_REF_CATS = ["math", "reasoning", "coding"]

# デフォルトのシステムプロンプトとユーザープロンプトテンプレート
DEFAULT_SYSTEM_PROMPT = """
Please act as an impartial judge and evaluate the quality of the response provided by an AI assistant to the user question displayed below. 
Your evaluation should consider factors such as the helpfulness, relevance, accuracy, depth, creativity, and level of detail of the response. 
Begin your evaluation by providing a short explanation. Be as objective as possible. 
The expected language is Japanese. Responses in languages other than Japanese will incur score deductions unless specifically required.
After providing your explanation, you must rate the response on a scale of 1 to 10 by strictly following this format: "[[rating]]", for example: "Rating: [[5]]".
"""

# Nejumiと同じプロンプト（一般タスク用）
NEJUMI_SYSTEM_PROMPT = """
あなたはAIアシスタントの回答の品質を評価する審査員です。与えられた質問とそれに対するAIアシスタントの回答を評価してください。
評価は以下の観点から行います：
1. 回答の正確性：提供された情報は正確か
2. 回答の完全性：質問に完全に答えているか
3. 回答の有用性：ユーザーの問題解決に役立つか
4. 表現の明確さ：わかりやすく説明されているか
5. 言語の適切さ：日本語として自然で適切か

評価を行った後、回答の品質を1から10の数値で評価してください。
10：完璧な回答（正確、完全、有用、明確、自然）
7-9：優れた回答（軽微な問題があるが、全体的に優れている）
4-6：許容できる回答（いくつかの問題があるが、基本的な情報は提供している）
1-3：不十分な回答（重大な問題がある、または質問に答えていない）

評価を記述した後、必ず「[[評価]]」の形式でスコアを記入してください。例：「[[8]]」
"""

# 数学・推論タスク用のプロンプト
NEJUMI_MATH_SYSTEM_PROMPT = """
あなたはAIアシスタントの回答の品質を評価する審査員です。与えられた問題と正解、そしてAIアシスタントの回答を評価してください。
評価は以下の観点から行います：
1. 回答の正確性：提供された情報や計算は正確か
2. 解法の適切さ：問題を解くアプローチは適切か
3. 説明の明確さ：解法や考え方が明確に説明されているか
4. 結論の正しさ：最終的な答えは正しいか

評価を行った後、回答の品質を1から10の数値で評価してください。
10：完璧な回答（正確な解法と答え、明確な説明）
7-9：優れた回答（軽微な問題があるが、解法と答えは正しい）
4-6：部分的に正しい（解法の方向性は正しいが、一部に誤りがある）
1-3：不正確または不完全（重大な誤りがある、または問題に答えていない）

評価を記述した後、必ず「[[評価]]」の形式でスコアを記入してください。例：「[[8]]」
"""

# シングルモード用のテンプレート
DEFAULT_PROMPT_TEMPLATE = """
[Question]
{question}

[The Start of Assistant's Answer]
{answer}
[The End of Assistant's Answer]
"""

# リファレンス付きのテンプレート
DEFAULT_REFERENCE_PROMPT_TEMPLATE = """
[Question]
{question}

[The Start of Reference Answer]
{reference}
[The End of Reference Answer]

[The Start of Assistant's Answer]
{answer}
[The End of Assistant's Answer]
"""

# ペアワイズ比較用のテンプレート
PAIRWISE_PROMPT_TEMPLATE = """
[Question]
{question}

[The Start of Assistant A's Answer]
{answer_a}
[The End of Assistant A's Answer]

[The Start of Assistant B's Answer]
{answer_b}
[The End of Assistant B's Answer]
"""

# ペアワイズ比較用のシステムプロンプト
PAIRWISE_SYSTEM_PROMPT = """
あなたは2つのAIアシスタントの回答を比較評価する審査員です。与えられた質問と2つのアシスタント（AとB）の回答を評価し、どちらの回答がより優れているかを判断してください。
評価は以下の観点から行います：
1. 回答の正確性：提供された情報は正確か
2. 回答の完全性：質問に完全に答えているか
3. 回答の有用性：ユーザーの問題解決に役立つか
4. 表現の明確さ：わかりやすく説明されているか
5. 言語の適切さ：日本語として自然で適切か

評価を行った後、両方の回答の品質を1から10の数値で評価し、次の形式で記入してください：「[[A_スコア,B_スコア]]」
例：「[[8,6]]」（Aの回答が8点、Bの回答が6点）

もし両方の回答が同等の品質であれば、同じスコアを付けることも可能です。評価の前に、それぞれの回答の長所と短所を簡潔に説明してください。
"""

# ペアワイズ比較（数学・推論）用のシステムプロンプト
PAIRWISE_MATH_SYSTEM_PROMPT = """
あなたは2つのAIアシスタントの回答を比較評価する審査員です。与えられた問題、正解、そして2つのアシスタント（AとB）の回答を評価し、どちらの回答がより優れているかを判断してください。
評価は以下の観点から行います：
1. 回答の正確性：提供された情報や計算は正確か
2. 解法の適切さ：問題を解くアプローチは適切か
3. 説明の明確さ：解法や考え方が明確に説明されているか
4. 結論の正しさ：最終的な答えは正しいか

評価を行った後、両方の回答の品質を1から10の数値で評価し、次の形式で記入してください：「[[A_スコア,B_スコア]]」
例：「[[8,6]]」（Aの回答が8点、Bの回答が6点）

もし両方の回答が同等の品質であれば、同じスコアを付けることも可能です。評価の前に、それぞれの回答の長所と短所を簡潔に説明してください。
"""


@register_metric
class LLMJudge(BaseMetric):
    """
    LLM as a judgeメトリクス
    
    強力なLLMを使用して、生成された回答の質を評価するメトリクス。
    10段階のスコアで評価し、結果を0.0-1.0の範囲に正規化します。
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初期化メソッド
        
        Args:
            parameters: 評価指標のパラメータ
        """
        super().__init__(name="llm_judge", parameters=parameters)
        self.is_higher_better = True
        
        # LiteLLMとオプション依存関係をインポート
        try:
            import litellm
            from litellm import acompletion
            self.litellm = litellm
            self.acompletion = acompletion
        except ImportError:
            raise ImportError("litellm is required for LLMJudge metric")

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        """
        LLM as a judgeメトリクスで使用可能なパラメータ定義
        
        Returns:
            Dict: パラメータ名とその定義（型、説明、デフォルト値など）の辞書
        """
        return {
            "judge_model": {
                "type": "string",
                "description": "評価に使用するLLMモデル",
                "default": "gpt-4-turbo",
                "required": False
            },
            "judge_provider": {
                "type": "string",
                "description": "評価に使用するプロバイダ",
                "default": "openai",
                "required": False
            },
            "system_prompt": {
                "type": "string",
                "description": "評価時に使用するシステムプロンプト",
                "default": DEFAULT_SYSTEM_PROMPT,
                "required": False
            },
            "prompt_template": {
                "type": "string",
                "description": "評価時に使用するプロンプトテンプレート",
                "default": DEFAULT_PROMPT_TEMPLATE,
                "required": False
            },
            "reference_prompt_template": {
                "type": "string",
                "description": "正解を含む評価時に使用するプロンプトテンプレート",
                "default": DEFAULT_REFERENCE_PROMPT_TEMPLATE,
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
                "default": 1024,
                "required": False
            },
            "temperature": {
                "type": "number",
                "description": "生成の温度パラメータ（カテゴリによって自動設定される場合もあります）",
                "default": 0.1,
                "required": False
            },
            "use_reference": {
                "type": "boolean",
                "description": "正解回答を使って評価するかどうか（カテゴリによって自動設定される場合もあります）",
                "default": False,
                "required": False
            },
            "scale_to_range": {
                "type": "boolean",
                "description": "10段階のスコアを0-1の範囲に変換するかどうか",
                "default": True,
                "required": False
            },
            "task_category": {
                "type": "string",
                "description": "タスクのカテゴリ（math, reasoning, coding, writing, roleplay, extraction, stemなど）",
                "default": "general",
                "required": False
            },
            "use_nejumi_prompts": {
                "type": "boolean",
                "description": "Nejumi互換のプロンプトを使用するかどうか",
                "default": True,
                "required": False
            },
            "mode": {
                "type": "string",
                "description": "評価モード（single または pairwise）",
                "default": "single",
                "enum": ["single", "pairwise"],
                "required": False
            },
            "two_score_pattern": {
                "type": "boolean",
                "description": "ペアワイズモードで2つのスコアを抽出するパターンを使用",
                "default": True,
                "required": False
            }
        }

    def _get_system_prompt(self) -> str:
        """
        タスクカテゴリと設定に基づいて適切なシステムプロンプトを取得
        
        Returns:
            str: 使用するシステムプロンプト
        """
        # 明示的に指定されている場合はそれを使用
        if "system_prompt" in self.parameters:
            return self.parameters["system_prompt"]
            
        # Nejumiプロンプトの使用が無効の場合はデフォルトを使用
        if not self.parameters.get("use_nejumi_prompts", True):
            return DEFAULT_SYSTEM_PROMPT
            
        # 評価モードを取得
        mode = self.parameters.get("mode", "single")
        
        # カテゴリを取得
        category = self.parameters.get("task_category", "general")
        
        # タスクカテゴリによるプロンプト選択
        if mode == "pairwise":
            # ペアワイズモード
            if category in NEED_REF_CATS:
                return PAIRWISE_MATH_SYSTEM_PROMPT
            return PAIRWISE_SYSTEM_PROMPT
        else:
            # シングルモード
            if category in NEED_REF_CATS:
                return NEJUMI_MATH_SYSTEM_PROMPT
            return NEJUMI_SYSTEM_PROMPT
    
    def _get_prompt_template(self, use_reference: bool = False) -> str:
        """
        設定に基づいて適切なプロンプトテンプレートを取得
        
        Args:
            use_reference: リファレンス回答を使用するかどうか
            
        Returns:
            str: 使用するプロンプトテンプレート
        """
        # モードを取得
        mode = self.parameters.get("mode", "single")
        
        if mode == "pairwise":
            # 明示的に指定されている場合はそれを使用
            if "prompt_template" in self.parameters:
                return self.parameters["prompt_template"]
            return PAIRWISE_PROMPT_TEMPLATE
        else:
            # シングルモード
            if use_reference:
                # リファレンス付きテンプレート
                if "reference_prompt_template" in self.parameters:
                    return self.parameters["reference_prompt_template"]
                return DEFAULT_REFERENCE_PROMPT_TEMPLATE
            else:
                # 通常のテンプレート
                if "prompt_template" in self.parameters:
                    return self.parameters["prompt_template"]
                return DEFAULT_PROMPT_TEMPLATE
    
    def _should_use_reference(self) -> bool:
        """
        タスクカテゴリと設定に基づいてリファレンス回答を使用するかどうかを決定
        
        Returns:
            bool: リファレンス回答を使用するかどうか
        """
        # 明示的に指定されている場合はそれを使用
        if "use_reference" in self.parameters:
            return self.parameters["use_reference"]
            
        # カテゴリによる決定
        category = self.parameters.get("task_category", "general")
        return category in NEED_REF_CATS
    
    def _get_temperature(self) -> float:
        """
        タスクカテゴリと設定に基づいて適切な温度パラメータを取得
        
        Returns:
            float: 使用する温度パラメータ
        """
        # 明示的に指定されている場合はそれを使用
        if "temperature" in self.parameters:
            return self.parameters["temperature"]
            
        # カテゴリによる決定
        category = self.parameters.get("task_category", "general")
        return TEMPERATURE_CONFIG.get(category, 0.1)

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        LLMを呼び出して評価を取得する内部メソッド
        
        Args:
            messages: LLMに送信するメッセージリスト
            
        Returns:
            str: LLMからの応答テキスト
        """
        judge_model = self.parameters.get("judge_model", "gpt-4-turbo")
        judge_provider = self.parameters.get("judge_provider", "openai")
        api_key = self.parameters.get("api_key", "")
        max_tokens = self.parameters.get("max_tokens", 1024)
        temperature = self._get_temperature()
        
        # プロバイダとモデルを結合（LiteLLMフォーマット）
        model_name = f"{judge_provider}/{judge_model}"
        
        # リクエストパラメータの設定
        request_params = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # APIキーが設定されている場合は追加
        if api_key:
            request_params["api_key"] = api_key
        
        try:
            # LLM呼び出し
            response = await self.acompletion(**request_params)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM評価中にエラーが発生しました: {e}")
            return ""

    def _extract_score(self, judgment: str) -> Union[float, Tuple[float, float]]:
        """
        評価レスポンスからスコアを抽出する
        
        Args:
            judgment: LLMからの評価レスポンス
            
        Returns:
            Union[float, Tuple[float, float]]: 抽出されたスコア (0-10) またはペアワイズスコアのタプル
        """
        mode = self.parameters.get("mode", "single")
        
        # ペアワイズモードで2つのスコアを抽出
        if mode == "pairwise" and self.parameters.get("two_score_pattern", True):
            match = TWO_SCORE_PATTERN.search(judgment)
            if not match:
                match = TWO_SCORE_PATTERN_BACKUP.search(judgment)
                
            if match:
                try:
                    score_a = float(match.group(1))
                    score_b = float(match.group(2))
                    
                    # スコアの範囲を確認
                    score_a = max(0.0, min(10.0, score_a))
                    score_b = max(0.0, min(10.0, score_b))
                    
                    return (score_a, score_b)
                except (ValueError, IndexError):
                    logger.warning(f"ペアワイズスコアの解析に失敗しました: {match.group(0)}")
                    return (0.0, 0.0)
        
        # 単一スコアを抽出
        match = RATING_PATTERN.search(judgment)
        if not match:
            # バックアップパターンで試行
            match = RATING_PATTERN_BACKUP.search(judgment)
            if not match:
                logger.warning(f"スコアが見つかりませんでした: {judgment}")
                return 0.0 if mode == "single" else (0.0, 0.0)
        
        try:
            score = float(match.group(1))
            # スコアの範囲を確認
            if score < 0:
                score = 0.0
            if score > 10:
                score = 10.0
                
            return score if mode == "single" else (score, 0.0)
        except (ValueError, IndexError):
            logger.warning(f"スコアの解析に失敗しました: {match.group(0)}")
            return 0.0 if mode == "single" else (0.0, 0.0)

    def calculate(self, hypothesis: str, reference: str, **kwargs) -> float:
        """
        LLMを使って回答を評価する
        
        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力または質問
            **kwargs: ペアワイズモード用の追加パラメータ
                hypothesis_b: モデルBの予測出力（ペアワイズモード用）
            
        Returns:
            float: 評価スコア (0.0-1.0)
        """
        # 評価モードを取得
        mode = self.parameters.get("mode", "single")
        
        # ペアワイズモードの場合
        if mode == "pairwise":
            # hypothesis_bパラメータを確認
            hypothesis_b = kwargs.get("hypothesis_b")
            if not hypothesis_b:
                logger.warning("ペアワイズモードでhypothesis_bが指定されていません。シングルモードにフォールバックします。")
                mode = "single"  # シングルモードにフォールバック
            else:
                return self._calculate_pairwise(hypothesis, hypothesis_b, reference)
        
        # シングルモードの処理
        return self._calculate_single(hypothesis, reference)
        
    def _calculate_single(self, hypothesis: str, reference: str) -> float:
        """
        単一回答を評価する（内部メソッド）
        
        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力または質問
            
        Returns:
            float: 評価スコア (0.0-1.0)
        """
        # パラメータ取得
        system_prompt = self._get_system_prompt()
        use_reference = self._should_use_reference()
        scale_to_range = self.parameters.get("scale_to_range", True)
        
        # プロンプトの準備
        question = reference  # タスク指示がreference引数に含まれています
        answer = hypothesis
        
        # メッセージの準備
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # プロンプトテンプレートの選択と適用
        prompt_template = self._get_prompt_template(use_reference)
        if use_reference:
            prompt = prompt_template.format(question=question, answer=answer, reference=reference)
        else:
            prompt = prompt_template.format(question=question, answer=answer)
            
        messages.append({"role": "user", "content": prompt})
        
        # 同期的に実行するため、非同期呼び出しをイベントループで実行
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # イベントループがない場合は新しく作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        judgment = loop.run_until_complete(self._call_llm(messages))
        
        # スコア抽出
        score = self._extract_score(judgment)
        
        # スコアを0-1の範囲に変換
        if scale_to_range:
            normalized_score = score / 10.0
            return normalized_score
        else:
            return score
            
    def _calculate_pairwise(self, hypothesis_a: str, hypothesis_b: str, reference: str) -> float:
        """
        ペアワイズ比較モードで回答を評価する（内部メソッド）
        
        Args:
            hypothesis_a: モデルAの予測出力
            hypothesis_b: モデルBの予測出力
            reference: 正解出力または質問
            
        Returns:
            float: モデルAの相対的な評価スコア (0.0-1.0)
        """
        # パラメータ取得
        system_prompt = self._get_system_prompt()
        use_reference = self._should_use_reference()
        scale_to_range = self.parameters.get("scale_to_range", True)
        
        # プロンプトの準備
        question = reference
        answer_a = hypothesis_a
        answer_b = hypothesis_b
        
        # メッセージの準備
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # プロンプトテンプレートの選択と適用
        prompt_template = self._get_prompt_template(use_reference)
        if use_reference:
            # リファレンス付きのテンプレートを拡張する必要がある場合はここに実装
            prompt = prompt_template.format(
                question=question, 
                answer_a=answer_a,
                answer_b=answer_b,
                reference=reference
            )
        else:
            prompt = prompt_template.format(
                question=question, 
                answer_a=answer_a,
                answer_b=answer_b
            )
            
        messages.append({"role": "user", "content": prompt})
        
        # 同期的に実行するため、非同期呼び出しをイベントループで実行
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # イベントループがない場合は新しく作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        judgment = loop.run_until_complete(self._call_llm(messages))
        
        # スコア抽出（ペアワイズモードではタプルを返す）
        scores = self._extract_score(judgment)
        
        if isinstance(scores, tuple):
            score_a, score_b = scores
            # TIE_DELTA = 0.1（Nejumiと同様）
            TIE_DELTA = 0.1
            
            # 同点の場合は0.5を返す
            if abs(score_a - score_b) <= TIE_DELTA:
                return 0.5 if scale_to_range else 5.0
                
            # モデルAのスコアを返す（相対的な評価）
            if scale_to_range:
                # ペアワイズの場合、勝敗に応じて0-1のスコアを返す
                return 1.0 if score_a > score_b else 0.0
            else:
                return score_a
        else:
            # スコアが単一値の場合、通常の処理を行う
            if scale_to_range:
                return scores / 10.0
            else:
                return scores

    async def calculate_async(self, hypothesis: str, reference: str, **kwargs) -> float:
        """
        LLMを使って回答を非同期に評価する
        
        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力または質問
            **kwargs: ペアワイズモード用の追加パラメータ
                hypothesis_b: モデルBの予測出力（ペアワイズモード用）
            
        Returns:
            float: 評価スコア (0.0-1.0)
        """
        # 評価モードを取得
        mode = self.parameters.get("mode", "single")
        
        # ペアワイズモードの場合
        if mode == "pairwise":
            # hypothesis_bパラメータを確認
            hypothesis_b = kwargs.get("hypothesis_b")
            if not hypothesis_b:
                logger.warning("ペアワイズモードでhypothesis_bが指定されていません。シングルモードにフォールバックします。")
                mode = "single"  # シングルモードにフォールバック
            else:
                return await self._calculate_pairwise_async(hypothesis, hypothesis_b, reference)
        
        # シングルモードの処理
        return await self._calculate_single_async(hypothesis, reference)

    async def _calculate_single_async(self, hypothesis: str, reference: str) -> float:
        """
        単一回答を非同期に評価する（内部メソッド）
        
        Args:
            hypothesis: モデルの予測出力
            reference: 正解出力または質問
            
        Returns:
            float: 評価スコア (0.0-1.0)
        """
        # パラメータ取得
        system_prompt = self._get_system_prompt()
        use_reference = self._should_use_reference()
        scale_to_range = self.parameters.get("scale_to_range", True)
        
        # プロンプトの準備
        question = reference
        answer = hypothesis
        
        # メッセージの準備
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # プロンプトテンプレートの選択と適用
        prompt_template = self._get_prompt_template(use_reference)
        if use_reference:
            prompt = prompt_template.format(question=question, answer=answer, reference=reference)
        else:
            prompt = prompt_template.format(question=question, answer=answer)
            
        messages.append({"role": "user", "content": prompt})
        
        # 非同期でLLMを呼び出し
        judgment = await self._call_llm(messages)
        
        # スコア抽出
        score = self._extract_score(judgment)
        
        # スコアを0-1の範囲に変換
        if scale_to_range:
            normalized_score = score / 10.0
            return normalized_score
        else:
            return score
    
    async def _calculate_pairwise_async(self, hypothesis_a: str, hypothesis_b: str, reference: str) -> float:
        """
        ペアワイズ比較モードで回答を非同期に評価する（内部メソッド）
        
        Args:
            hypothesis_a: モデルAの予測出力
            hypothesis_b: モデルBの予測出力
            reference: 正解出力または質問
            
        Returns:
            float: モデルAの相対的な評価スコア (0.0-1.0)
        """
        # パラメータ取得
        system_prompt = self._get_system_prompt()
        use_reference = self._should_use_reference()
        scale_to_range = self.parameters.get("scale_to_range", True)
        
        # プロンプトの準備
        question = reference
        answer_a = hypothesis_a
        answer_b = hypothesis_b
        
        # メッセージの準備
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # プロンプトテンプレートの選択と適用
        prompt_template = self._get_prompt_template(use_reference)
        if use_reference:
            # リファレンス付きのテンプレートを拡張する必要がある場合はここに実装
            prompt = prompt_template.format(
                question=question, 
                answer_a=answer_a,
                answer_b=answer_b,
                reference=reference
            )
        else:
            prompt = prompt_template.format(
                question=question, 
                answer_a=answer_a,
                answer_b=answer_b
            )
            
        messages.append({"role": "user", "content": prompt})
        
        # 非同期でLLMを呼び出し
        judgment = await self._call_llm(messages)
        
        # スコア抽出（ペアワイズモードではタプルを返す）
        scores = self._extract_score(judgment)
        
        if isinstance(scores, tuple):
            score_a, score_b = scores
            # TIE_DELTA = 0.1（Nejumiと同様）
            TIE_DELTA = 0.1
            
            # 同点の場合は0.5を返す
            if abs(score_a - score_b) <= TIE_DELTA:
                return 0.5 if scale_to_range else 5.0
                
            # モデルAのスコアを返す（相対的な評価）
            if scale_to_range:
                # ペアワイズの場合、勝敗に応じて0-1のスコアを返す
                return 1.0 if score_a > score_b else 0.0
            else:
                return score_a
        else:
            # スコアが単一値の場合、通常の処理を行う
            if scale_to_range:
                return scores / 10.0
            else:
                return scores