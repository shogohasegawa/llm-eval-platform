# LLM as a Judge メトリクス

LLM as a Judge（LLMによる評価）は、GPT-4などの高性能言語モデルを使用して、他のモデルの出力を評価するメトリクスです。これにより、人間の評価者が行うような主観的な品質評価を自動化できます。

## 概要

従来の自動評価メトリクス（BLEU、F1スコアなど）は参照回答との文字列の一致度を測定しますが、LLM as a Judgeはモデル出力の品質、有用性、正確性などを総合的に評価します。GPT-4などの強力なモデルを「ジャッジ」として使用することで、より人間の判断に近い評価を得ることができます。

## 使用方法

### 1. データセット設定

データセット定義ファイル（JSON）にLLMJudgeメトリクスを追加します：

```json
{
  "name": "my_dataset",
  "metrics": [
    {
      "name": "llm_judge",
      "parameters": {
        "judge_model": "gpt-4",
        "judge_provider": "openai",
        "system_prompt": "あなたは公平な評価者です...",
        "scale_to_range": true
      }
    },
    "exact_match",
    "char_f1"
  ],
  "instruction": "以下の質問に対して適切な回答を作成してください。",
  "samples": [...]
}
```

### 2. パラメータ設定

LLMJudgeメトリクスは様々なパラメータをサポートしています：

- **judge_model**: 評価に使用するLLMモデル（例：gpt-4, gpt-4-turbo）
- **judge_provider**: モデルプロバイダー（例：openai, anthropic）
- **system_prompt**: 評価指示を含むシステムプロンプト
- **prompt_template**: 評価用プロンプトテンプレート
- **api_key**: APIキー（設定されていない場合は環境変数から取得）
- **max_tokens**: 応答の最大トークン数
- **temperature**: 生成の温度
- **use_reference**: 参照回答を評価に使用するかどうか
- **scale_to_range**: 10段階のスコアを0-1の範囲に変換するかどうか

### 3. 評価の実行

通常の評価ワークフローでLLM as a Judgeメトリクスを使用できます：

```python
await run_evaluation(
    dataset_name="llm_judge_sample",
    provider_name="openai",
    model_name="gpt-3.5-turbo",
    num_samples=10,
    n_shots=[0]
)
```

## プロンプトテンプレート

LLM as a Judgeメトリクスには2種類のプロンプトテンプレートがあります：

1. **基本テンプレート** (参照回答なし):
```
[Question]
{question}

[The Start of Assistant's Answer]
{answer}
[The End of Assistant's Answer]
```

2. **参照回答付きテンプレート** (use_reference=True):
```
[Question]
{question}

[The Start of Reference Answer]
{reference}
[The End of Reference Answer]

[The Start of Assistant's Answer]
{answer}
[The End of Assistant's Answer]
```

## スコアの解釈

LLMジャッジは1-10の範囲でスコアを返します。デフォルトではスケーリング（scale_to_range=True）が有効になっており、このスコアは0-1の範囲に正規化されます。

- **0.0-0.3**: 不十分な回答
- **0.4-0.6**: 許容できる回答
- **0.7-0.8**: 良い回答
- **0.9-1.0**: 優れた回答

## 実装上の注意

- LLM as a Judgeメトリクスは外部APIを呼び出すため、評価にかかる時間やコストが他のメトリクスより高くなります
- APIキーや課金設定に注意してください
- 大規模なデータセットの評価にはリソース管理が重要です

## カスタマイズ

独自の評価基準やプロンプトで評価を行いたい場合は、パラメータを調整することで様々な評価スタイルを実現できます。例えば：

- 特定のタスク（数学、論理、創造性）に特化した評価
- 有害性や倫理的問題の評価
- 多段階評価（複数の観点からそれぞれスコアを付ける）

## Nejumi Leaderboardとの互換性

LLM as a Judgeメトリクスは、[Nejumi Leaderboard](https://github.com/wandb/llm-leaderboard)のLLM評価アプローチと互換性があります。Nejumiは特に日本語LLMの評価に特化しており、LLMを使った評価手法を採用しています。

### Nejumiの評価手法

Nejumiでは主に以下の評価手法を採用しています：

1. **MT-Bench**: マルチターン会話評価用のベンチマーク
2. **Toxicity Evaluation**: 有害コンテンツ生成傾向の評価
3. **LLM as a Judge**: 様々なタスクにおけるLLMの回答品質評価

本実装では、Nejumiと同様のLLM as a Judge機能を提供し、同等の評価方法で結果を得ることができます。

### Nejumiとの主な違い

- Nejumiでは主にタスク特化型の評価プロンプトを使用していますが、本実装ではより汎用的なプロンプトをデフォルトとしています
- Nejumiでは一般的にGPT-4を評価モデルとして使用していますが、本実装では任意のLLMを評価モデルとして使用できます
- Nejumiでは評価結果をWandBに記録しますが、本実装ではMLflowに記録することもできます

## トラブルシューティング

### APIエラー

```
LLM評価中にエラーが発生しました: Error: 401 Unauthorized
```

- APIキーが正しく設定されているか確認してください
- プロバイダーの課金設定を確認してください

### スコア抽出エラー

```
スコアが見つかりませんでした: [評価文]
```

- システムプロンプトで正しいフォーマット（"[[rating]]"）を指定しているか確認してください
- 異なるモデルを試してみてください

### レート制限エラー

```
LLM評価中にエラーが発生しました: Error: 429 Too Many Requests
```

- 一度に実行する評価の数を減らしてください
- 評価間の間隔を空けるために`max_concurrent_requests`パラメータを調整してください