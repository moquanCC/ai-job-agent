from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "real_jobs"

# The independent annotator was better calibrated than the keyword-assisted first pass.
# These two cases are intentionally lowered after adjudication because each candidate
# lacks direct evidence for a core specialization named by the role.
OVERRIDES = {
    ("eval_llm", "real_shlab_003"): (2, "具备 LLM/RAG 工程基础，但岗位核心包含脑科学智能体研究，简历无脑科学或专项智能体证据，裁决为相关但有明显缺口。"),
    ("eval_nlp", "real_shlab_002"): (2, "NLP、PyTorch 与 LLM 背景方向一致，但现有项目是文本分类，未直接证明大模型数据合成、预训练或 SFT/RL 能力，裁决为 2 而非高度匹配。"),
}


def index_rows(path: Path) -> dict[tuple[str, str], dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    index = {(row["candidate_id"], row["job_id"]): row for row in rows}
    if len(index) != len(rows):
        raise ValueError(f"duplicate candidate-job pair in {path}")
    return index


def main() -> None:
    first = index_rows(DATA / "relevance_labels.json")
    second = index_rows(DATA / "relevance_labels_second.json")
    if first.keys() != second.keys():
        raise ValueError("annotator coverage differs")

    gold = []
    adjudicated = 0
    for key in sorted(first):
        first_row = first[key]
        second_row = second[key]
        first_grade = int(first_row["grade"])
        second_grade = int(second_row["grade"])
        if first_grade == second_grade:
            grade = first_grade
            decision = "agreement"
            rationale = f"两位标注者一致为 {grade}。{second_row['rationale']}"
        elif key in OVERRIDES:
            grade, rationale = OVERRIDES[key]
            decision = "adjudicator_override"
            adjudicated += 1
        else:
            grade = second_grade
            decision = "adopt_independent_review"
            rationale = f"首标为关键词规则辅助结果，复标对候选人证据与岗位核心要求进行了逐项比较；裁决采用复标 {grade} 级。{second_row['rationale']}"
            adjudicated += 1
        gold.append(
            {
                "candidate_id": key[0],
                "job_id": key[1],
                "grade": grade,
                "annotator": "adjudicated-model-panel-v1",
                "rationale": rationale,
                "labeled_at": "2026-08-12",
                "decision": decision,
                "first_grade": first_grade,
                "second_grade": second_grade,
            }
        )

    if len(gold) != 90 or len({(row["candidate_id"], row["job_id"]) for row in gold}) != 90:
        raise ValueError("gold label coverage must contain exactly 90 unique pairs")
    (DATA / "relevance_gold.json").write_text(json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pairs": len(gold), "adjudicated": adjudicated, "grades": Counter(row["grade"] for row in gold)}, ensure_ascii=False, default=dict))


if __name__ == "__main__":
    main()
