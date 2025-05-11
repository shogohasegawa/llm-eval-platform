import json
from pathlib import Path
from typing import Optional

def convert_japanese_mtbench_to_jaster(
    question_path: Path,
    ref_answer_path: Optional[Path] = None,
    model_answer_path: Optional[Path] = None,
    category_filter: Optional[str] = None,
    output_dir: Path = Path("."),
    output_path: Optional[Path] = None,
    max_tokens: int = 1024,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        filename = f"japanese_mtbench_{category_filter}.json" if category_filter else "japanese_mtbench_all.json"
        output_path = output_dir / filename

    questions = {}
    categories = set()
    with question_path.open(encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            if category_filter is None or item["category"] == category_filter:
                questions[item["question_id"]] = {
                    "turns": item["turns"],
                    "category": item["category"],
                    "question_id": item["question_id"]
                }
                categories.add(item["category"])

    ref_answers = {}
    if ref_answer_path and ref_answer_path.exists():
        with ref_answer_path.open(encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                qid = item["question_id"]
                if qid in questions:
                    ref_answers[qid] = item["choices"][0]["turns"]

    model_answers = {}
    if model_answer_path and model_answer_path.exists():
        with model_answer_path.open(encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                qid = item["question_id"]
                if qid in questions:
                    model_answers[qid] = item["choices"][0]["turns"]

    need_ref_cats = ["math", "reasoning", "coding"]
    
    samples = []
    for qid, qdata in questions.items():
        category = qdata["category"]
        turns = qdata["turns"]
        
        sample = {
            "id": str(qid),
            "input1": turns[0],
            "input2": turns[1] if len(turns) > 1 else "",
        }

        if category in need_ref_cats and qid in ref_answers:
            sample["output1"] = ref_answers[qid][0] if len(ref_answers[qid]) > 0 else ""
            sample["output2"] = ref_answers[qid][1] if len(ref_answers[qid]) > 1 else ""
        elif qid in model_answers:
            sample["output1"] = model_answers[qid][0] if len(model_answers[qid]) > 0 else ""
            sample["output2"] = model_answers[qid][1] if len(model_answers[qid]) > 1 else ""
        else:
            sample["output1"] = ""
            sample["output2"] = ""
                
        samples.append(sample)

    temperature_config = {
        "writing": 0.7,
        "roleplay": 0.7,
        "extraction": 0.0,
        "math": 0.0,
        "coding": 0.0,
        "reasoning": 0.0,
        "stem": 0.1,
        "humanities": 0.1,
        "general": 0.1,
    }

    instruction = ""

    metrics_config = {
        "temperature": temperature_config.get(category_filter, 0.1) if category_filter else 0.1,
        "multi_turn": True
    }

    jaster_data = {
        "instruction": instruction,
        "output_length": max_tokens,
        "metrics": ["llm_as_a_judge"],
        "metrics_config": metrics_config,
        "few_shots": [],
        "samples": samples
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(jaster_data, f, indent=2, ensure_ascii=False)

    print(f"{len(samples)} 件を {output_path} に保存しました。")

    if any(cat in need_ref_cats for cat in categories):
        ref_cnt = sum(1 for s in samples if s.get('output1') and category_filter in need_ref_cats)
        print(f"  math/reasoning/codingカテゴリのサンプル: {ref_cnt}/{len([s for s in samples if category_filter in need_ref_cats])}")
        if ref_cnt == 0:
            print("  警告: 参照回答が必要なカテゴリですが、参照回答がありません。")

# ---------------------
# 実行例 (__main__)
# ---------------------
if __name__ == "__main__":
    categories = [
        "coding",
        "extraction",
        "humanities",
        "math",
        "reasoning",
        "roleplay",
        "stem",
        "writing",
    ]

    ref_answer_path = Path(
        "/Users/shogohasegawa/develop_apps/mcp_projects/shared/wandb_download/artifacts/mtbench_ja_referenceanswer:v2/base-gpt4o-with-human-annotation.jsonl"
    )

    model_answer_path = None  # モデル回答があればここに指定

    for category in categories:
        convert_japanese_mtbench_to_jaster(
            question_path=Path(
                "/Users/shogohasegawa/develop_apps/mcp_projects/shared/wandb_download/artifacts/mtbench_ja_question:v4/question.jsonl"
            ),
            ref_answer_path=ref_answer_path,
            model_answer_path=model_answer_path,
            category_filter=category,
            output_dir=Path(
                "/Users/shogohasegawa/develop_apps/mcp_projects/shared/llm-eval-platform/datasets/test/"
            ),
            max_tokens=1024
        )
