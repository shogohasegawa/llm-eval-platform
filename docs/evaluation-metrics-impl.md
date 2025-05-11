# LLM評価プラットフォームの評価指標構成

このドキュメントは、LLM評価プラットフォームおよび参考プロジェクト「llm-leaderboard」（Nejumi Leaderboard 3）で使用されている評価指標の構成について、実装に基づいて詳細にまとめたものです。各データセット（ベンチマーク）の役割と評価指標の算出フローに焦点を当てています。

## 目次

1. [評価フレームワークの全体構造](#評価フレームワークの全体構造)
2. [GLP（汎用的言語性能）](#glp汎用的言語性能)
3. [ALT（アラインメント）](#altアラインメント)
4. [評価プロセスの流れ](#評価プロセスの流れ)
5. [スコア集計方法](#スコア集計方法)

## 評価フレームワークの全体構造

LLM評価プラットフォームは、「GLP（汎用的言語性能）」と「ALT（アラインメント）」という2つの主軸で構成されています。コードの`aggregate.py`を中心に見ていくと、それぞれの軸に複数のサブカテゴリが含まれ、各サブカテゴリは複数のベンチマークタスクから構成されています。

```python
# aggregate.pyの例
if GLP_flag:
    leaderboard_dict["GLP_表現"] = calculate_combined_means([],["roleplay","writing","humanities"])
    leaderboard_dict["GLP_翻訳"] = calculate_combined_means(["alt-e-to-j","alt-j-to-e","wikicorpus-e-to-j","wikicorpus-j-to-e"], [])
    # ...その他のGLPサブカテゴリ...
    leaderboard_dict["汎用的言語性能(GLP)_AVG"] = calculate_average_from_dict(leaderboard_dict, "GLP")

if ALT_flag:
    leaderboard_dict["ALT_制御性"] = np.mean([np.mean([jaster_control_0shot["AVG"][0], jaster_control_fewshots["AVG"][0]]), lctg_overall["AVG_Total_ctg"][0]])
    # ...その他のALTサブカテゴリ...
    leaderboard_dict["アラインメント(ALT)_AVG"] = calculate_average_from_dict(leaderboard_dict, "ALT")
```

## GLP（汎用的言語性能）

GLPは10の主要サブカテゴリから構成され、言語モデルの能力を多面的に評価します。

### 1. GLP_表現

**使用ベンチマーク**: MT-bench（roleplay, humanities, writing）  
**データ構成**: 各カテゴリに複数の質問  
**サンプル数**: 各カテゴリ数十問  
**評価設定**: 0-shot  
**評価方法**: GPT-4o-2024-05-13を評価モデルとして使用（10点満点）  
**スコア計算**:
```python
# MT-benchスコアを10で割って正規化
leaderboard_dict["GLP_表現"] = calculate_combined_means([],["roleplay","writing","humanities"])
```

### 2. GLP_翻訳

**使用ベンチマーク**: ALT e-to-j, ALT j-to-e, wikicorpus-e-to-j, wikicorpus-j-to-e（すべてjasterの一部）  
**データ構成**: 英日・日英翻訳のペア  
**サンプル数**: テスト用100サンプル、バリデーション用10サンプル  
**評価設定**: 0-shot, 2-shot  
**評価方法**: comet_wmt22メトリクス  
**スコア計算**:
```python
# 0-shotと2-shotの結果を平均
leaderboard_dict["GLP_翻訳"] = calculate_combined_means(["alt-e-to-j","alt-j-to-e","wikicorpus-e-to-j","wikicorpus-j-to-e"], [])
```

### 3. GLP_情報検索

**使用ベンチマーク**: JSQuaD  
**データ構成**: 文書と質問のペア  
**サンプル数**: テスト用100サンプル、バリデーション用10サンプル  
**評価設定**: 0-shot, 2-shot  
**評価方法**: exact_matchメトリクス  
**スコア計算**:
```python
leaderboard_dict["GLP_情報検索"] = calculate_combined_means(["jsquad"], [])
```

### 4. GLP_推論

**使用ベンチマーク**: MT-bench（reasoning）  
**データ構成**: 推論を要する質問  
**サンプル数**: 数十問  
**評価設定**: 0-shot  
**評価方法**: GPT-4o-2024-05-13による評価（10点満点）  
**スコア計算**:
```python
leaderboard_dict["GLP_推論"] = calculate_combined_means([], ["reasoning"])
```

### 5. GLP_数学的推論

**使用ベンチマーク**: MAWPS, MGSM, MT-bench（math）  
**データ構成**: 数学的問題  
**サンプル数**:
- MAWPS, MGSM: テスト用100サンプル、バリデーション用10サンプル
- MT-bench（math）: 数十問  
**評価設定**: 
- MAWPS, MGSM: 0-shot, 2-shot
- MT-bench（math）: 0-shot  
**評価方法**: 
- MAWPS, MGSM: exact_match_figureメトリクス
- MT-bench（math）: GPT-4o-2024-05-13による評価  
**スコア計算**:
```python
leaderboard_dict["GLP_数学的推論"] = calculate_combined_means(["mawps","mgsm"], ["math"])
```

### 6. GLP_抽出

**使用ベンチマーク**: wiki_ner, wiki_coreference, chabsa（chABSA）, MT-bench（extraction）  
**データ構成**: 固有表現や関係性の抽出タスク  
**サンプル数**: 
- wiki_ner, wiki_coreference, chabsa: テスト用20サンプル、バリデーション用5サンプル
- MT-bench（extraction）: 数十問  
**評価設定**: 
- wiki_ner, wiki_coreference, chabsa: 0-shot, 2-shot
- MT-bench（extraction）: 0-shot  
**評価方法**: タスク固有の評価メトリクス  
**スコア計算**:
```python
leaderboard_dict["GLP_抽出"] = calculate_combined_means(["wiki_ner", "wiki_coreference", "chabsa"], ["extraction"])
```

### 7. GLP_知識・質問応答

**使用ベンチマーク**: JCommonsenseQA, JEMHopQA, JMMLU, NIILC, aio, MT-bench（stem）  
**データ構成**: 知識ベースの質問応答  
**サンプル数**: 
- JCommonsenseQA, JEMHopQA, NIILC, aio: テスト用100サンプル、バリデーション用10サンプル
- JMMLU: テスト用5サンプル、バリデーション用1サンプル
- MT-bench（stem）: 数十問  
**評価設定**: 
- JCommonsenseQA, JEMHopQA, JMMLU, NIILC, aio: 0-shot, 2-shot
- MT-bench（stem）: 0-shot  
**評価方法**: exact_matchおよびGPT-4o-2024-05-13による評価  
**スコア計算**:
```python
leaderboard_dict["GLP_知識・質問応答"] = calculate_combined_means(["jcommonsenseqa","jemhopqa", "jmmlu","niilc","aio"], ["stem"])
```

### 8. GLP_英語

**使用ベンチマーク**: MMLU_en  
**データ構成**: 英語での多様な分野の質問  
**サンプル数**: テスト用5サンプル、バリデーション用1サンプル  
**評価設定**: 0-shot, 2-shot  
**評価方法**: exact_matchメトリクス  
**スコア計算**:
```python
leaderboard_dict["GLP_英語"] = calculate_combined_means(["mmlu_en"], [])
```

### 9. GLP_意味解析

**使用ベンチマーク**: JNLI, JaNLI, JSeM, JSICK, Jamp  
**データ構成**: 文間の意味的関係タスク  
**サンプル数**: テスト用100サンプル、バリデーション用10サンプル  
**評価設定**: 0-shot, 2-shot  
**評価方法**: タスク固有の評価メトリクス  
**スコア計算**:
```python
leaderboard_dict["GLP_意味解析"] = calculate_combined_means(["jnli","janli","jsem","jsick", "jamp"], [])
```

### 10. GLP_構文解析

**使用ベンチマーク**: JCoLA-in-domain, JCoLA-out-of-domain, JBLiMP, wiki_reading, wiki_pas, wiki_dependency  
**データ構成**: 文法性判断や構文関係タスク  
**サンプル数**: 
- JCoLA-in-domain, JCoLA-out-of-domain, JBLiMP: テスト用100サンプル、バリデーション用10サンプル
- wiki_reading, wiki_pas, wiki_dependency: テスト用20サンプル、バリデーション用5サンプル  
**評価設定**: 0-shot, 2-shot  
**評価方法**: タスク固有の評価メトリクス  
**スコア計算**:
```python
leaderboard_dict["GLP_構文解析"] = calculate_combined_means(["jcola-in-domain","jcola-out-of-domain","jblimp","wiki_reading","wiki_pas","wiki_dependency"], [])
```

### GLP全体スコア

GLPの全体スコアは、上記10のサブカテゴリの平均値として計算されます：

```python
leaderboard_dict["汎用的言語性能(GLP)_AVG"] = calculate_average_from_dict(leaderboard_dict, "GLP")
```

## ALT（アラインメント）

ALTは6つの主要サブカテゴリから構成され、モデルの安全性や価値観との整合性を評価します。

### 1. ALT_制御性

**使用ベンチマーク**: jaster（制御性評価部分）, LCTG  
**データ構成**: 
- jaster: 各タスクの制御性評価
- LCTG: 指示に従う能力評価  
**サンプル数**: 
- jaster: テスト用100サンプル、バリデーション用10サンプル
- LCTG: タスク固有の設定  
**評価設定**: 0-shot, 2-shot（jaster）  
**評価方法**: 
- jaster: タスク固有の制御性メトリクス
- LCTG: 量的評価（quantity test）  
**スコア計算**:
```python
leaderboard_dict["ALT_制御性"] = np.mean([np.mean([jaster_control_0shot["AVG"][0], jaster_control_fewshots["AVG"][0]]), lctg_overall["AVG_Total_ctg"][0]])
```

### 2. ALT_倫理・道徳

**使用ベンチマーク**: JCommonsenseMorality（jaster内）  
**データ構成**: 倫理的判断を要するシナリオ  
**サンプル数**: テスト用100サンプル、バリデーション用10サンプル  
**評価設定**: 2-shot  
**評価方法**: タスク固有の評価メトリクス  
**スコア計算**:
```python
leaderboard_dict["ALT_倫理・道徳"] = jaster_fewshots["commonsensemoralja"][0]
```

### 3. ALT_毒性

**使用ベンチマーク**: LINE Yahoo Reliability Evaluation Benchmark  
**データ構成**: 有害コンテンツの生成リスク評価  
**サンプル数**: 非公開  
**評価設定**: タスク固有の設定  
**評価方法**: 「公平性」「社会規範」「禁止行為」「違反カテゴリ」の4項目での評価  
**スコア計算**:
```python
leaderboard_dict["ALT_毒性"] = toxicity[["公平性", "社会規範", "禁止行為", "違反カテゴリ"]].values.mean()
```

### 4. ALT_バイアス

**使用ベンチマーク**: JBBQ  
**データ構成**: 年齢、障害、性別アイデンティティなどのカテゴリに関するバイアス評価  
**サンプル数**: 各カテゴリからテスト用20サンプル、バリデーション用4サンプル  
**評価設定**: 2-shot  
**評価方法**: 
- 曖昧な文脈（ambig）と明確な文脈（disambig）
- ネガティブ・ポジティブな質問
- ステレオタイプに一致する/しない回答の分析  
**スコア計算**:
```python
leaderboard_dict["ALT_バイアス"] = 1 - jbbq_fewshots["avg_abs_bias_score"][0]
```

### 5. ALT_堅牢性

**使用ベンチマーク**: JMMLU（複数パターン）
- 標準的な選択肢
- 記号選択肢（SymbolChoice）
- 不正解選択肢（IncorrectChoice）  
**データ構成**: JMMLUデータセットの異なるプロンプトパターン  
**サンプル数**: テスト用5サンプル、バリデーション用1サンプル  
**評価設定**: 0-shot, 2-shot  
**評価方法**: 異なるプロンプトパターンでの回答一貫性の評価  
**スコア計算**:
```python
leaderboard_dict["ALT_堅牢性"] = jmmlu_robust_fewshots["robust_score"][0]
```

### 6. ALT_真実性

**使用ベンチマーク**: JTruthfulQA  
**データ構成**: 事実に基づく質問  
**サンプル数**: タスク固有の設定  
**評価設定**: タスク固有の設定  
**評価方法**: RoBERTaモデル（nlp-waseda/roberta_jtruthfulqa）による評価  
**スコア計算**:
```python
leaderboard_dict["ALT_真実性"] = jtruthfulqa["overall_score"][0]
```

### ALT全体スコア

ALTの全体スコアは、上記6のサブカテゴリの平均値として計算されます：

```python
leaderboard_dict["アラインメント(ALT)_AVG"] = calculate_average_from_dict(leaderboard_dict, "ALT")
```

## 評価プロセスの流れ

実装コードを詳細に分析すると、評価プロセスは以下のような流れになっています：

1. **データセット準備**：
   ```python
   # データセットのダウンロード（jaster.py より）
   artifact = run.use_artifact(cfg[dataset_name].artifacts_path, type="dataset")
   artifact_dir = artifact.download()
   dataset_dir = Path(artifact_dir) / cfg[dataset_name].dataset_dir
   ```

2. **推論処理**：
   - 各タスクでは、0-shotあるいは2-shotの設定でモデルに入力を作成
   - LLMAsyncProcessorを使用して並列処理
   ```python
   llm_ap = LLMAsyncProcessor(
       llm=llm,
       inputs=all_inputs,
   )
   results = llm_ap.get_results()
   ```

3. **出力処理と評価**：
   - モデル出力をタスク特有の方法で処理（text_formatter関数など）
   - 適切な評価メトリクスを適用
   ```python
   # jaster.pyの例
   y_pred: str = pipe(
       raw_output,
       lambda x: text_formatter(x, evaluation_result["task"]),
       lambda x: x.split("\n\n")[0],
       lambda x: x.strip(),
       lambda x: x.strip("'").strip('"'),
       lambda x: x.strip(),
       normalize,
   )
   metrics_func = evaluation_result["metrics_func"]
   score = metrics_func(y_pred, evaluation_result["expected_output"])
   ```

4. **結果集計**：
   - テスト用サブセットのみを使用して最終スコアを計算
   - 0-shotと2-shotの結果を平均化
   - サブカテゴリ、カテゴリレベルでスコアを集計
   ```python
   # aggregate.pyより
   leaderboard_dict["GLP_表現"] = calculate_combined_means([],["roleplay","writing","humanities"])
   # ...他のサブカテゴリ...
   leaderboard_dict["汎用的言語性能(GLP)_AVG"] = calculate_average_from_dict(leaderboard_dict, "GLP")
   ```

5. **総合評価**：
   - GLPとALTの両方が利用可能な場合、総合スコアを計算
   ```python
   if GLP_flag and ALT_flag:
       leaderboard_dict["TOTAL_AVG"] = np.mean([leaderboard_dict["汎用的言語性能(GLP)_AVG"], leaderboard_dict["アラインメント(ALT)_AVG"]])
   ```

## スコア集計方法

スコア集計の核となる関数は`calculate_combined_means`で、jasterベンチマークとMT-benchの結果を組み合わせる役割を果たします：

```python
def calculate_combined_means(cols_jaster, cols_mtbench):
    means = []
    if cols_jaster:
        for col in cols_jaster:
            mean_value = (jaster_0shot[col][0] + jaster_fewshots[col][0]) / 2
            means.append(mean_value)

    if cols_mtbench:
        for col in cols_mtbench:
            means.append(mtbench[col][0] / 10)
    return np.mean(means)
```

この関数は：
1. jasterベースのタスクでは、0-shotと2-shotの平均値を計算（両方の設定で評価した場合）
2. MT-benchタスクでは、10点満点のスコアを10で割って正規化
3. すべてのスコアの平均値を返す

また、サブカテゴリのスコアから主要カテゴリの平均値を計算するための関数も用意されています：

```python
def calculate_average_from_dict(data_dict, prefix):
    relevant_items = {key: value for key, value in data_dict.items() if key.startswith(prefix)}
    relevant_values = [value for value in relevant_items.values() if isinstance(value, (int, float))]
    if relevant_values:
        return sum(relevant_values) / len(relevant_values)
    return float('nan')
```

この実装により、階層的なスコア計算が可能になり、個別のベンチマークから総合的な言語能力評価まで、一貫した方法でモデルのパフォーマンスを測定できます。
