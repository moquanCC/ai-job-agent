from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.matching.filters import filter_jobs
from src.models.schemas import JobProfile


VERSION = "human-gold-readiness-v1"
SEED = 20260812
DEFAULT_OUTPUT = ROOT / "data" / "human_gold"

ARCHETYPES = [
    ("llm_rag", "大语言模型与RAG", ["Python", "PyTorch", "LLM", "RAG", "FAISS"]),
    ("nlp", "自然语言处理", ["Python", "PyTorch", "NLP", "Transformer", "文本分类"]),
    ("computer_vision", "计算机视觉", ["Python", "PyTorch", "OpenCV", "目标检测", "图像分割"]),
    ("multimodal", "多模态", ["Python", "PyTorch", "CLIP", "VLM", "图文检索"]),
    ("recommendation", "推荐系统", ["Python", "SQL", "推荐系统", "特征工程", "召回排序"]),
    ("data_mining", "数据挖掘", ["Python", "SQL", "机器学习", "数据挖掘", "XGBoost"]),
    ("search_ads", "搜索与广告", ["Python", "C++", "搜索排序", "广告CTR", "Learning to Rank"]),
    ("ai_infra", "AI基础设施", ["Python", "C++", "CUDA", "分布式训练", "Docker"]),
    ("agents", "智能体", ["Python", "Agent", "工具调用", "工作流编排", "FastAPI"]),
    ("autonomous_driving", "自动驾驶", ["Python", "C++", "感知", "规划控制", "点云"]),
    ("ai_testing", "AI评测与测试", ["Python", "模型评测", "测试自动化", "数据质量", "安全评测"]),
]
DEGREES = ["本科", "硕士", "博士"]
STRENGTHS = ["strong", "medium", "limited"]


def _candidate(index: int) -> dict:
    key, label, base_skills = ARCHETYPES[index % len(ARCHETYPES)]
    variant = index // len(ARCHETYPES) + 1
    degree = DEGREES[(index * 2 + variant) % len(DEGREES)]
    strength = STRENGTHS[(index + variant) % len(STRENGTHS)]
    candidate_id = f"synthetic_{index + 1:02d}_{key}"
    achievement = {
        "strong": "完成端到端系统并在冻结测试集上取得明确量化提升",
        "medium": "完成课程或实验室项目并记录可复现实验结果",
        "limited": "完成基础原型和公开数据集练习，暂无实习或论文证据",
    }[strength]
    skills = [*base_skills, "Git"] if variant % 2 else [*base_skills, "Linux"]
    evidence_items = [
        f"{label}项目变体{variant}：{achievement}",
        f"使用{skills[0]}与{skills[1]}完成核心模块，保留代码和实验记录",
    ]
    text = (
        f"合成候选人 {candidate_id}\n教育：{degree}，计算机相关专业\n"
        f"目标方向：{label}\n技能：{'、'.join(skills)}\n"
        f"项目证据：{'；'.join(evidence_items)}\n"
        "声明：该画像为评测用途的合成候选人，不对应任何真实个人。"
    )
    return {
        "candidate_id": candidate_id,
        "synthetic": True,
        "role_family": key,
        "role_family_label": label,
        "education": {"degree": degree, "major": "计算机相关专业"},
        "skills": skills,
        "evidence": {"strength": strength, "items": evidence_items},
        "text": text,
    }


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _eligible_jobs() -> list[JobProfile]:
    records = json.loads((ROOT / "data" / "real_jobs" / "jobs.json").read_text(encoding="utf-8"))
    active = [JobProfile.model_validate(row) for row in records if row["status"] == "active"]
    return sorted(filter_jobs(active), key=lambda job: job.job_id)


def generate_dataset(output_dir: str | Path = DEFAULT_OUTPUT) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    candidates = [_candidate(index) for index in range(30)]
    candidate_ids = [candidate["candidate_id"] for candidate in candidates]
    shuffled = candidate_ids.copy()
    random.Random(SEED).shuffle(shuffled)
    splits = {
        "train": sorted(shuffled[:18]),
        "validation": sorted(shuffled[18:24]),
        "blind_test": sorted(shuffled[24:]),
    }
    split_for = {
        candidate_id: split
        for split, ids in splits.items()
        for candidate_id in ids
    }

    eligible_jobs = _eligible_jobs()
    if len(eligible_jobs) < 25:
        raise ValueError(f"可用公开 JD 不足 25 条，当前仅 {len(eligible_jobs)} 条")
    selected_jobs = eligible_jobs[:25]
    tasks = [
        {
            "task_id": f"{candidate_id}__{job.job_id}",
            "candidate_id": candidate_id,
            "job_id": job.job_id,
            "split": split_for[candidate_id],
            "synthetic_candidate": True,
            "human_gold": False,
            "grade": None,
            "rationale": None,
            "confidence": None,
        }
        for candidate_id in sorted(candidate_ids)
        for job in selected_jobs
    ]

    candidate_bytes = _json_bytes(candidates)
    task_bytes = _json_bytes(tasks)
    fingerprint = hashlib.sha256(candidate_bytes + task_bytes).hexdigest()
    manifest = {
        "version": VERSION,
        "seed": SEED,
        "synthetic_candidates": True,
        "human_gold": False,
        "status": "annotation_tasks_not_completed",
        "all_candidate_ids": sorted(candidate_ids),
        "candidate_splits": splits,
        "counts": {
            "candidates": len(candidates),
            "train": len(splits["train"]),
            "validation": len(splits["validation"]),
            "blind_test": len(splits["blind_test"]),
            "pairs": len(tasks),
        },
        "eligible_job_count": len(eligible_jobs),
        "selected_job_count": len(selected_jobs),
        "selected_job_ids": [job.job_id for job in selected_jobs],
        "pair_count": len(tasks),
        "fingerprint_algorithm": "sha256(candidates.json bytes + annotation_tasks.json bytes)",
        "sha256_fingerprint": fingerprint,
    }
    paths = {
        "candidates": output / "candidates.json",
        "manifest": output / "split_manifest.json",
        "tasks": output / "annotation_tasks.json",
    }
    paths["candidates"].write_bytes(candidate_bytes)
    paths["tasks"].write_bytes(task_bytes)
    paths["manifest"].write_bytes(_json_bytes(manifest))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate frozen synthetic human-annotation readiness data.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    paths = generate_dataset(args.output)
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
