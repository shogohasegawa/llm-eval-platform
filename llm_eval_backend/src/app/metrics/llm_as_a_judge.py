from typing import Dict, Any, Optional
from app.metrics.base import BaseMetric, register_metric, ParamDef
from typing import Union, List
from litellm import completion
import re
import logging
from app.utils.db.providers import get_api_key_by_provider_name

logger = logging.getLogger(__name__)

# マルチターン一般タスク用のシングル評価プロンプト
MULTI_TURN_DEFAULT_SYSTEM_PROMPT = """Please act as an impartial judge and evaluate the quality of the response provided by an AI assistant to the user question displayed below. Your evaluation should consider factors such as the helpfulness, relevance, accuracy, depth, creativity, and level of detail of the response. You evaluation should focus on the assistant's answer to the second user question. Begin your evaluation by providing a short explanation. Be as objective as possible. The expected language is Japanese. Responses in languages other than Japanese will incur score deductions unless specifically required. Failure to use Japanese at all will result in the lowest evaluation. However, using Japanese is not mandatory when providing only Python scripts or calculation results, where Japanese is not essential. Additionally, your explanation of judgement should be in Japanese. After providing your explanation, you must rate the response on a scale of 1 to 10 by strictly following this format: "[[rating]]", for example: "Rating: [[5]]".
"""

# 評価スコアを抽出するための正規表現パターン
RATING_PATTERN = re.compile(r"\[\[(\d+(?:\.\d+)?)\]\]")
RATING_PATTERN_BACKUP = re.compile(r"\[(\d+(?:\.\d+)?)\]")

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
                "required": False
            },
            "multi_turn": {
                "type": "boolean",
                "description": "マルチターン評価を実行するかどうか",
                "default": True,
                "required": False
            },
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

    def calculate(self, hypothesis: Union[str, List[str]], reference: Union[str, List[str]], **kwargs) -> float:
        """
        LLMを呼び出して応答を評価し、スコアを0〜1に正規化して返します。

        Args:
            hypothesis (str | List[str]): AIの応答文または応答文のリスト
            reference (str | List[str]): 正解文または正解文のリスト
            question (str | List[str]): ユーザーからの質問文またはそのリスト

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

        # 適切なプロンプトを選択
        system_prompt = MULTI_TURN_DEFAULT_SYSTEM_PROMPT
        
        # メッセージの準備
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # promptの生成
        # もしreferenceの要素0が空であれば、referenceは使用しない
        if reference[0] == "":
            with_reference = False
        else:
            with_reference = True
        prompt_template = build_multi_turn_prompt_template(len(hypothesis), with_reference=with_reference)

        # プレースホルダに埋め込む辞書を作成
        format_dict = {}
        for i in range(len(hypothesis)):
            format_dict[f"question_{i+1}"] = question[i]
            format_dict[f"hypothesis_{i+1}"] = hypothesis[i]
            format_dict[f"reference_{i+1}"] = reference[i]


        # テンプレートに値を埋め込む
        prompt = prompt_template.format(**format_dict)

        # メッセージに追加
        messages.append({"role": "user", "content": prompt})

        # パラメータの取得
        judge_model = self.parameters.get("judge_model", "gpt-4o-2024-05-13")
        judge_provider = self.parameters.get("judge_provider", "openai")
        api_key = self.parameters.get("api_key", "")   
        max_tokens = self.parameters.get("max_tokens", 2048)

        api_key = get_api_key_by_provider_name(judge_provider)
        # 推論の実行
        completion_response = completion(
            model=judge_model,
            messages=messages,
            api_key=api_key,
            max_tokens=max_tokens
        )

        print(completion_response)

        # レスポンス本文を取り出す
        response_text = completion_response.choices[0].message.content

        # スコアを抽出
        score = self._extract_score(response_text)        
        score = score / 10.0
        return score

# if __name__ == "__main__":
#     # テスト用の仮説と参照
#     hypothesis = ["今日は日曜日です", "雨が降るでしょう"]
#     reference = [
#         "もちろんです。以下は、指定されたディレクトリ内の全てのテキストファイルを読み込み、出現回数が最も多い上位5単語を返すPythonプログラムの例です。\n\n```python\nimport os\nimport re\nfrom collections import Counter\n\ndef read_text_files(directory):\n    text = \"\"\n    for filename in os.listdir(directory):\n        if filename.endswith(\".txt\"):\n            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as file:\n                text += file.read() + \" \"\n    return text\n\ndef get_top_words(text, top_n=5):\n    # 単語を抽出し、すべて小文字に変換\n    words = re.findall(r'\\b\\w+\\b', text.lower())\n    # 単語の出現回数をカウント\n    word_counts = Counter(words)\n    # 出現回数が多い上位の単語を取得\n    top_words = word_counts.most_common(top_n)\n    return top_words\n\ndef main(directory):\n    text = read_text_files(directory)\n    top_words = get_top_words(text)\n    for word, count in top_words:\n        print(f\"{word}: {count}\")\n\n# 使用例\ndirectory_path = \"your_directory_path_here\"  # ここにディレクトリのパスを指定してください\nmain(directory_path)\n```\n\n### プログラムの説明\n1. **`read_text_files` 関数**:\n    - 指定されたディレクトリ内の全てのテキストファイルを読み込み、1つの文字列として結合します。\n2. **`get_top_words` 関数**:\n    - テキストから単語を抽出し、小文字に変換します。\n    - 単語の出現回数をカウントし、上位 `top_n` 個の単語を返します。\n3. **`main` 関数**:\n    - ディレクトリパスを受け取り、テキストを読み込み、上位の単語を表示します。\n\n### 使用方法\n1. `directory_path` 変数に対象のディレクトリのパスを指定します。\n2. プログラムを実行すると、指定されたディレクトリ内の全てのテキストファイルを読み込み、出現回数が最も多い上位5単語が表示されます。\n\nこのプログラムは、基本的なテキスト処理とファイル操作を行うための良い出発点となります。必要に応じて、さらに機能を追加したり、改善したりすることができます。", 
#         "はい、Pythonで並列処理を行うことは可能です。並列処理を行うための方法として、`concurrent.futures` モジュールを使用するのが一般的です。このモジュールを使うことで、複数のファイルを並列に読み込むことができます。\n\n以下は、先ほどのプログラムを並列化したバージョンです。\n\n```python\nimport os\nimport re\nfrom collections import Counter\nfrom concurrent.futures import ThreadPoolExecutor\n\ndef read_text_file(filepath):\n    with open(filepath, 'r', encoding='utf-8') as file:\n        return file.read()\n\ndef read_text_files_parallel(directory):\n    text = \"\"\n    with ThreadPoolExecutor() as executor:\n        futures = []\n        for filename in os.listdir(directory):\n            if filename.endswith(\".txt\"):\n                filepath = os.path.join(directory, filename)\n                futures.append(executor.submit(read_text_file, filepath))\n        \n        for future in futures:\n            text += future.result() + \" \"\n    return text\n\ndef get_top_words(text, top_n=5):\n    words = re.findall(r'\\b\\w+\\b', text.lower())\n    word_counts = Counter(words)\n    top_words = word_counts.most_common(top_n)\n    return top_words\n\ndef main(directory):\n    text = read_text_files_parallel(directory)\n    top_words = get_top_words(text)\n    for word, count in top_words:\n        print(f\"{word}: {count}\")\n\n# 使用例\ndirectory_path = \"your_directory_path_here\"  # ここにディレクトリのパスを指定してください\nmain(directory_path)\n```\n\n### プログラムの説明\n1. **`read_text_file` 関数**:\n    - 単一のテキストファイルを読み込み、その内容を返します。\n2. **`read_text_files_parallel` 関数**:\n    - `ThreadPoolExecutor` を使用して、ディレクトリ内の全てのテキストファイルを並列に読み込みます。\n    - 各ファイルの読み込みタスクをスレッドプールに送信し、結果を結合します。\n3. **`get_top_words` 関数**:\n    - テキストから単語を抽出し、小文字に変換します。\n    - 単語の出現回数をカウントし、上位 `top_n` 個の単語を返します。\n4. **`main` 関数**:\n    - ディレクトリパスを受け取り、テキストを並列に読み込み、上位の単語を表示します。\n\n### 使用方法\n1. `directory_path` 変数に対象のディレクトリのパスを指定します。\n2. プログラムを実行すると、指定されたディレクトリ内の全てのテキストファイルを並列に読み込み、出現回数が最も多い上位5単語が表示されます。\n\nこのプログラムは、`ThreadPoolExecutor` を使用してファイルの読み込みを並列化することで、処理速度を向上させることができます。ファイル数が多い場合や、各ファイルのサイズが大きい場合に特に有効です。",
#         ]
#     question = [
#         "ディレクトリ内の全てのテキストファイルを読み込み、出現回数が最も多い上位5単語を返すPythonプログラムを開発してください。", 
#         "それを並列化（parallelize）することは可能ですか？",
#         ]

#     # LLMJudgeのインスタンスを作成
#     llm_judge = LlmJudge()

#     # 評価を実行
#     score = llm_judge.calculate(hypothesis, reference, question=question)
#     print(f"評価スコア: {score:.2f}")

