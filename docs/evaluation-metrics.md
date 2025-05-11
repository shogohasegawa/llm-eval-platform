# LLM評価プラットフォームにおける評価指標の構成

このドキュメントは、参考プロジェクト「llm-leaderboard」（Nejumi Leaderboard 3）で使用されている評価指標（GLP_XXXやALT_XXX）の構成について詳細にまとめたものです。

## 目次

1. [概要](#概要)
2. [評価指標の全体像](#評価指標の全体像)
3. [GLP（汎用的言語性能）](#glp汎用的言語性能)
   - [GLP_表現](#glp_表現)
   - [GLP_翻訳](#glp_翻訳)
   - [GLP_情報検索](#glp_情報検索)
   - [GLP_推論](#glp_推論)
   - [GLP_数学的推論](#glp_数学的推論)
   - [GLP_抽出](#glp_抽出)
   - [GLP_知識・質問応答](#glp_知識質問応答)
   - [GLP_英語](#glp_英語)
   - [GLP_意味解析](#glp_意味解析)
   - [GLP_構文解析](#glp_構文解析)
4. [ALT（アラインメント）](#altアラインメント)
   - [ALT_制御性](#alt_制御性)
   - [ALT_倫理・道徳](#alt_倫理道徳)
   - [ALT_毒性](#alt_毒性)
   - [ALT_バイアス](#alt_バイアス)
   - [ALT_堅牢性](#alt_堅牢性)
   - [ALT_真実性](#alt_真実性)
5. [評価手法](#評価手法)
   - [few-shot設定](#few-shot設定)
   - [スコア計算方法](#スコア計算方法)
6. [結果の統合方法](#結果の統合方法)

## 概要

LLM評価プラットフォームでは、主に2つの大きな観点からLLMの性能を評価しています：

1. **GLP（汎用的言語性能）**: 言語モデルとしての基本的な能力や知識を評価
2. **ALT（アラインメント）**: 人間の価値観との整合性を評価

これらの評価指標は、複数のデータセットやタスクを組み合わせて構成されており、0-shotと2-shotの両方の設定で評価が行われ、その平均値が最終スコアとなっています。

## 評価指標の全体像

以下の表は、主要な評価カテゴリとそれを構成するデータセット・タスクの概要です：

| メインカテゴリ | サブカテゴリ | データセット/タスク | 推論設定 | 説明 |
|--------------|------------|-------------------|---------|------|
| GLP（汎用的言語性能） | 表現 | MT-bench（roleplay, humanities, writing） | 0-shot | 文章生成や表現力の評価 |
| ^ | 翻訳 | ALT e-to-j, ALT j-to-e, wikicorpus-e-to-j, wikicorpus-j-to-e | 0-shot, 2-shot | 英日・日英翻訳の評価 |
| ^ | 情報検索 | JSQuaD | 0-shot, 2-shot | 質問応答タスクによる情報検索能力の評価 |
| ^ | 推論 | MT-bench（reasoning） | 0-shot | 推論能力の評価 |
| ^ | 数学的推論 | MAWPS, MGSM, MT-bench（math） | 0-shot, 2-shot | 数学的問題解決能力の評価 |
| ^ | 抽出 | wiki_ner, wiki_coreference, chABSA, MT-bench（extraction） | 0-shot, 2-shot | 固有表現抽出などの評価 |
| ^ | 知識・質問応答 | JCommonsenseQA, JEMHopQA, JMMLU, NIILC, aio, MT-bench（stem） | 0-shot, 2-shot | 常識的知識や専門知識の評価 |
| ^ | 英語 | MMLU_en | 0-shot, 2-shot | 英語での知識評価 |
| ^ | 意味解析 | JNLI, JaNLI, JSeM, JSICK, Jamp | 0-shot, 2-shot | 意味的関係や含意関係の理解の評価 |
| ^ | 構文解析 | JCoLA-in-domain, JCoLA-out-of-domain, JBLiMP, wiki_reading, wiki_pas, wiki_dependency | 0-shot, 2-shot | 文法性判断や構文理解の評価 |
| ALT（アラインメント） | 制御性 | jaster, LCTG | 0-shot, 2-shot | 特定の制約や条件に従う能力の評価 |
| ^ | 倫理・道徳 | JCommonsenseMorality | 2-shot | 倫理的・道徳的判断の評価 |
| ^ | 毒性 | LINE Yahoo Reliability Evaluation Benchmark | - | 有害なコンテンツを生成しない能力の評価 |
| ^ | バイアス | JBBQ | 2-shot | 偏見・バイアスの評価 |
| ^ | 堅牢性 | JMMLU（複数パターン） | 0-shot, 2-shot | 入力の変化に対する堅牢性の評価 |
| ^ | 真実性 | JTruthfulQA | - | 真実の情報を提供する能力の評価 |

## GLP（汎用的言語性能）

GLP（汎用的言語性能）は10の主要サブカテゴリに分かれており、モデルの言語能力を多角的に評価します。

### GLP_表現

**データセット**: MT-bench（roleplay, humanities, writing）  
**サンプル数**: 各カテゴリ数十問  
**推論設定**: 0-shot  
**評価方法**: GPT-4o（2024-05-13）を用いた自動評価  
**スコア計算**: MT-benchスコア（10点満点）を10で割った値を使用  
**特徴**: ロールプレイ、人文科学的質問、文章作成能力を評価

### GLP_翻訳

**データセット**: ALT e-to-j, ALT j-to-e, wikicorpus-e-to-j, wikicorpus-j-to-e  
**サンプル数**: テスト用100サンプル（test_max_num_samples）、バリデーション用10サンプル（val_max_num_samples）  
**推論設定**: 0-shot, 2-shot（両方の平均）  
**評価方法**: comet_wmt22メトリクスによる自動評価  
**スコア計算**: 0-shotと2-shotの各データセットのスコアの平均値  
**特徴**: 英日・日英の両方向の翻訳能力を評価

### GLP_情報検索

**データセット**: JSQuaD  
**サンプル数**: テスト用100サンプル、バリデーション用10サンプル  
**推論設定**: 0-shot, 2-shot（両方の平均）  
**評価方法**: exact_matchメトリクスによる自動評価  
**スコア計算**: 0-shotと2-shotのスコアの平均値  
**特徴**: 質問応答タスクにより情報検索能力を評価

### GLP_推論

**データセット**: MT-bench（reasoning）  
**サンプル数**: 数十問  
**推論設定**: 0-shot  
**評価方法**: GPT-4o（2024-05-13）を用いた自動評価  
**スコア計算**: MT-benchスコア（10点満点）を10で割った値を使用  
**特徴**: 論理的推論能力を評価

### GLP_数学的推論

**データセット**: MAWPS, MGSM, MT-bench（math）  
**サンプル数**: 
- MAWPS, MGSM: テスト用100サンプル、バリデーション用10サンプル
- MT-bench（math）: 数十問  
**推論設定**: 
- MAWPS, MGSM: 0-shot, 2-shot（両方の平均）
- MT-bench（math）: 0-shot  
**評価方法**: 
- MAWPS, MGSM: exact_match_figureメトリクスによる自動評価
- MT-bench（math）: GPT-4o（2024-05-13）を用いた自動評価  
**スコア計算**: MAWPS, MGSMの0-shotと2-shotのスコア、およびMT-benchスコア（10点満点を10で割った値）の平均値  
**特徴**: 数学的問題解決能力を評価

### GLP_抽出

**データセット**: wiki_ner, wiki_coreference, chABSA（chabsa）, MT-bench（extraction）  
**サンプル数**: 
- wiki_ner, wiki_coreference, chABSA: テスト用20サンプル、バリデーション用5サンプル
- MT-bench（extraction）: 数十問  
**推論設定**: 
- wiki_ner, wiki_coreference, chABSA: 0-shot, 2-shot（両方の平均）
- MT-bench（extraction）: 0-shot  
**評価方法**: 
- wiki_ner, wiki_coreference, chABSA: タスク固有の評価メトリクス
- MT-bench（extraction）: GPT-4o（2024-05-13）を用いた自動評価  
**スコア計算**: 各データセットのスコアの平均値  
**特徴**: 固有表現抽出、共参照解析、感情分析などの抽出能力を評価

### GLP_知識・質問応答

**データセット**: JCommonsenseQA, JEMHopQA, JMMLU, NIILC, aio, MT-bench（stem）  
**サンプル数**: 
- JCommonsenseQA, JEMHopQA, NIILC, aio: テスト用100サンプル、バリデーション用10サンプル
- JMMLU: テスト用5サンプル、バリデーション用1サンプル
- MT-bench（stem）: 数十問  
**推論設定**: 
- JCommonsenseQA, JEMHopQA, JMMLU, NIILC, aio: 0-shot, 2-shot（両方の平均）
- MT-bench（stem）: 0-shot  
**評価方法**: 
- JCommonsenseQA, JEMHopQA, JMMLU, NIILC, aio: exact_matchメトリクスによる自動評価
- MT-bench（stem）: GPT-4o（2024-05-13）を用いた自動評価  
**スコア計算**: 各データセットのスコアの平均値  
**特徴**: 常識的知識や科学・技術・工学・数学（STEM）分野の知識を評価

### GLP_英語

**データセット**: MMLU_en  
**サンプル数**: テスト用5サンプル、バリデーション用1サンプル  
**推論設定**: 0-shot, 2-shot（両方の平均）  
**評価方法**: exact_matchメトリクスによる自動評価  
**スコア計算**: 0-shotと2-shotのスコアの平均値  
**特徴**: 英語での多様な分野の知識を評価

### GLP_意味解析

**データセット**: JNLI, JaNLI, JSeM, JSICK, Jamp  
**サンプル数**: テスト用100サンプル、バリデーション用10サンプル  
**推論設定**: 0-shot, 2-shot（両方の平均）  
**評価方法**: タスク固有の評価メトリクス  
**スコア計算**: 各データセットの0-shotと2-shotのスコアの平均値  
**特徴**: 自然言語推論、含意関係、意味的等価性の理解を評価

### GLP_構文解析

**データセット**: JCoLA-in-domain, JCoLA-out-of-domain, JBLiMP, wiki_reading, wiki_pas, wiki_dependency  
**サンプル数**: 
- JCoLA-in-domain, JCoLA-out-of-domain, JBLiMP: テスト用100サンプル、バリデーション用10サンプル
- wiki_reading, wiki_pas, wiki_dependency: テスト用20サンプル、バリデーション用5サンプル  
**推論設定**: 0-shot, 2-shot（両方の平均）  
**評価方法**: タスク固有の評価メトリクス  
**スコア計算**: 各データセットの0-shotと2-shotのスコアの平均値  
**特徴**: 文法性判断、構文理解、依存関係解析などの言語構造理解を評価

## ALT（アラインメント）

ALT（アラインメント）は6つの主要サブカテゴリに分かれており、モデルが人間の価値観や期待に沿っているかを評価します。

### ALT_制御性

**データセット**: jaster（制御性評価部分）, LCTG  
**サンプル数**: 
- jaster: テスト用100サンプル、バリデーション用10サンプル
- LCTG: タスク固有の設定  
**推論設定**: 0-shot, 2-shot（両方の平均）  
**評価方法**: 
- jaster: タスク固有の制御性メトリクス
- LCTG: 量的評価（quality test）  
**スコア計算**: jaster（0-shotと2-shotの平均）とLCTGの平均値  
**特徴**: モデルが指示や制約に従う能力を評価

### ALT_倫理・道徳

**データセット**: JCommonsenseMorality（jaster内）  
**サンプル数**: テスト用100サンプル、バリデーション用10サンプル  
**推論設定**: 2-shot（主に2-shotの結果を使用）  
**評価方法**: タスク固有の評価メトリクス  
**スコア計算**: 2-shotのスコアを使用  
**特徴**: 倫理的・道徳的状況における判断能力を評価

### ALT_毒性

**データセット**: LINE Yahoo Reliability Evaluation Benchmark  
**サンプル数**: 非公開（センシティブな内容のため）  
**推論設定**: タスク固有の設定  
**評価方法**: 「公平性」「社会規範」「禁止行為」「違反カテゴリ」の4項目での評価  
**スコア計算**: 4項目のスコアの平均値  
**特徴**: 有害なコンテンツを生成しない能力を評価

### ALT_バイアス

**データセット**: JBBQ  
**サンプル数**: 各カテゴリ（年齢、障害、性別アイデンティティなど）からテスト用20サンプル、バリデーション用4サンプル  
**推論設定**: 2-shot  
**評価方法**: バイアススコアの計算
- 曖昧な文脈（ambig）と明確な文脈（disambig）
- ネガティブ・ポジティブな質問
- ステレオタイプに一致する/しない回答の分析  
**スコア計算**: 1 - avg_abs_bias_score（バイアスの絶対値の平均を1から引いた値）  
**特徴**: 社会的バイアスや偏見の有無を評価

### ALT_堅牢性

**データセット**: JMMLU（複数パターン）
- 標準的な選択肢
- 記号選択肢（SymbolChoice）
- 不正解選択肢（IncorrectChoice）  
**サンプル数**: テスト用5サンプル、バリデーション用1サンプル  
**推論設定**: 0-shot, 2-shot  
**評価方法**: 異なるパターンの選択肢でのロバスト性評価  
**スコア計算**: 堅牢性スコア（robust_score）の計算  
**特徴**: 入力形式の変化に対する堅牢性を評価

### ALT_真実性

**データセット**: JTruthfulQA  
**サンプル数**: タスク固有の設定  
**推論設定**: タスク固有の設定  
**評価方法**: RoBERTaモデル（nlp-waseda/roberta_jtruthfulqa）による評価  
**スコア計算**: 総合スコア（overall_score）  
**特徴**: 真実の情報を提供し、誤った情報を避ける能力を評価

## 評価手法

### few-shot設定

多くのタスクでは0-shotと2-shotの両方の設定で評価が行われます：

- **0-shot**: タスクに関する説明と入力のみを提供し、具体例なしでモデルが回答
- **2-shot**: タスクの説明と入力に加えて、2つの例（入力と正解）を提供してからモデルが回答

例外として、MT-benchは基本的に0-shotのみ、JCommonsenseMoralityとJBBQは主に2-shotのみで評価されます。

### スコア計算方法

各タスクにはそれぞれ適切な評価メトリクスが使用されます：

- **exact_match**: 完全一致による評価
- **exact_match_figure**: 数値の完全一致による評価
- **comet_wmt22**: 翻訳評価のためのメトリクス
- **MT-benchスコア**: GPT-4oによる採点（0-10点）
- **バイアススコア**: JBBQにおける複数指標の計算
- **RoBERTaモデル評価**: JTruthfulQAにおける真実性評価

## 結果の統合方法

評価結果は以下のように階層的に統合されます：

1. **タスクレベル**: 
   - 0-shotと2-shotの結果の平均（適用可能な場合）
   - 複数のサブタスクの結果の平均

2. **サブカテゴリレベル**:
   - GLP_XXXやALT_XXXなどのサブカテゴリごとに、関連するタスクの結果を平均化

3. **カテゴリレベル**:
   - GLP（汎用的言語性能）: 10個のサブカテゴリの平均値
   - ALT（アラインメント）: 6個のサブカテゴリの平均値

4. **総合評価**:
   - TOTAL_AVG: GLPとALTの平均値による総合評価

このように、複数の異なるタスクやデータセットを組み合わせることで、言語モデルの能力を多角的かつ包括的に評価する仕組みが構築されています。
