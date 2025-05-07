#!/usr/bin/env python3
"""
大量のサンプルデータを含むデータセットを生成するスクリプト
ページネーションのテスト用
"""
import json
import os
import random
from pathlib import Path

# ランダム文章を生成するヘルパー関数
def generate_random_text(words=10):
    word_list = [
        "AI", "人工知能", "機械学習", "深層学習", "自然言語処理", "コンピュータビジョン", 
        "ロボティクス", "強化学習", "教師あり学習", "教師なし学習", "半教師あり学習", 
        "転移学習", "ニューラルネットワーク", "データ", "アルゴリズム", "モデル", 
        "パラメータ", "ハイパーパラメータ", "特徴量", "バックプロパゲーション",
        "勾配降下法", "活性化関数", "損失関数", "エポック", "バッチサイズ", 
        "正則化", "過学習", "過少学習", "精度", "再現率", "F値", "ROC曲線"
    ]
    return " ".join(random.choices(word_list, k=random.randint(words, words+10)))

# 質問と回答のペアを生成
def generate_question_answer_pair(index):
    topics = [
        "AIの歴史について教えてください。",
        "機械学習の基本原理を説明してください。",
        "ディープラーニングとは何ですか？",
        "自然言語処理の最新技術について教えてください。",
        "強化学習の応用例を挙げてください。",
        "ニューラルネットワークの構造について説明してください。",
        "AIの倫理的問題とは何ですか？",
        "生成AIについて説明してください。",
        "機械翻訳の仕組みを教えてください。",
        "コンピュータビジョンの応用例を教えてください。"
    ]
    
    # ランダムな質問を選択または生成
    if random.random() < 0.7 and topics:
        question = random.choice(topics)
    else:
        question = f"テストサンプル質問 {index}: {generate_random_text(5)}"
    
    # 回答を生成
    answer_length = random.randint(1, 5)  # 段落数
    answer = "\n\n".join([generate_random_text(15) for _ in range(answer_length)])
    
    return question, answer

# メインの関数
def create_large_dataset(num_samples=100, output_path=None):
    """大量のサンプルを含むデータセットを生成"""
    if not output_path:
        output_path = Path("/home/shogohasegawa/workspace/llm-eval-platform/datasets/test/large_dataset.json")
    else:
        output_path = Path(output_path)
    
    # データセットの基本構造
    dataset = {
        "name": "large_dataset",
        "description": f"ページネーションテスト用大規模データセット ({num_samples}サンプル)",
        "metrics": ["char_f1", "exact_match"],
        "instruction": "以下の質問に対して適切な回答を作成してください。",
        "output_length": 1024,
        "samples": []
    }
    
    # サンプルデータを生成
    for i in range(1, num_samples + 1):
        question, answer = generate_question_answer_pair(i)
        sample = {
            "id": f"large_sample_{i}",
            "input": question,
            "output": answer,
            "additional_data": {
                "sample_index": i,
                "created": "2025-05-08",
                "metrics": {
                    "char_f1": random.random(),
                    "exact_match": random.random() < 0.2
                }
            }
        }
        dataset["samples"].append(sample)
    
    # データセットをJSONとして保存
    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"{num_samples}サンプルを含むデータセットを作成しました: {output_path}")
    return output_path

if __name__ == "__main__":
    # 200サンプルのデータセットを作成
    create_large_dataset(200)