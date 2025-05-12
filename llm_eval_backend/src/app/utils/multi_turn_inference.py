import json
import os
import time
import concurrent.futures
import shortuuid
import tqdm
from litellm import completion

# --- 会話履歴を管理するクラス ---
class Conversation:
    def __init__(self, system_message="You are a helpful assistant."):
        self.system_message = system_message  # system prompt
        self.roles = ("user", "assistant")   # user / assistant のロール名
        self.messages = []  # 会話履歴: List[Tuple[role, message]]

    def append_message(self, role, message):
        """会話履歴にメッセージを追加"""
        self.messages.append([role, message])

    def update_last_message(self, message):
        """最後のメッセージ（通常 assistant の None）を置き換える"""
        self.messages[-1][1] = message

    def to_openai_api_messages(self):
        """LiteLLM/OpenAI互換の messages 形式に変換"""
        messages = []
        if self.system_message:
            messages.append({"role": "system", "content": self.system_message})
        for role, msg in self.messages:
            if role == self.roles[0]:  # user
                messages.append({"role": "user", "content": msg})
            elif role == self.roles[1]:  # assistant
                if msg is not None:
                    messages.append({"role": "assistant", "content": msg})
        return messages

# --- 質問ファイルの読み込み ---
def load_questions(question_file: str):
    """JSONL形式の質問ファイルを読み込む"""
    questions = []
    with open(question_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                q = json.loads(line)
                q["question_id"] = int(q["question_id"])
                questions.append(q)
    return questions

# --- 全体の推論処理 ---
def get_api_answer(
    question_file,
    answer_file,
    model_name,
    api_key,
    num_worker=1,
    num_choices=1,
    max_tokens=512,
    temperature=0.7
):
    """
    質問ファイルを読み込み、モデルで回答を生成して出力ファイルに保存する。

    Args:
        question_file: 質問が記載されたJSONLファイルパス
        answer_file: 回答出力先のJSONLファイルパス
        model_name: 使用するモデル名（litellm経由）
        api_key: 使用するAPI key
        num_worker: 並列実行数
        num_choices: 各質問に対する候補生成数
        max_tokens: 生成最大トークン数
        temperature: 生成時のtemperature（カテゴリに関係なく固定）
    """
    questions = load_questions(question_file)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_worker) as executor:
        futures = [
            executor.submit(
                get_answer,
                question,
                model_name,
                api_key,
                num_choices,
                max_tokens,
                temperature,
                answer_file
            )
            for question in questions
        ]

        for future in tqdm.tqdm(
            concurrent.futures.as_completed(futures), total=len(futures)
        ):
            try:
                future.result()
            except Exception as e:
                print(f"Function raised an exception: {e}")

# --- 単一質問に対する回答生成処理 ---
def get_answer(question, model_name, api_key, num_choices, max_tokens, temperature, answer_file):
    """1つの質問に対してモデルで回答を生成し、結果をファイルに追記する"""

    choices = []
    for i in range(num_choices):
        conv = Conversation()  # chatgpt風

        # ユーザー発話ごとに1ターンずつ構築（multi-turn想定）
        for turn in question["turns"]:
            conv.append_message(conv.roles[0], turn)
            conv.append_message(conv.roles[1], None)

            # LiteLLMを使ったAPI呼び出し
            response = completion(
                model=model_name,
                api_key=api_key,
                messages=conv.to_openai_api_messages(),
                temperature=temperature,
                max_tokens=max_tokens
            )

            output = response["choices"][0]["message"]["content"]
            conv.update_last_message(output)

        # assistant側の発話だけを抽出
        turns = [msg[1] for msg in conv.messages if msg[0] == conv.roles[1]]
        choices.append({"index": i, "turns": turns})

    ans = {
        "question_id": question["question_id"],
        "answer_id": shortuuid.uuid(),
        "model_id": model_name,
        "choices": choices,
        "tstamp": time.time(),
    }

    # 出力先ディレクトリがあれば作成（カレントディレクトリのときはスキップ）
    dir_path = os.path.dirname(answer_file)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(answer_file, "a", encoding="utf-8") as fout:
        fout.write(json.dumps(ans, ensure_ascii=False) + "\n")
