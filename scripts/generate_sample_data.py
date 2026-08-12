from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "evaluation"

ROLES = [
    ("大模型应用工程师", ["Python", "大语言模型", "检索增强生成", "FAISS"], ["FastAPI", "Docker"]),
    ("机器学习算法工程师", ["Python", "机器学习", "PyTorch", "深度学习"], ["SQL", "Docker"]),
    ("数据挖掘工程师", ["Python", "数据挖掘", "机器学习", "SQL"], ["推荐系统", "PyTorch"]),
    ("搜索推荐算法工程师", ["Python", "推荐系统", "机器学习", "PyTorch"], ["大语言模型", "SQL"]),
    ("NLP算法工程师", ["Python", "自然语言处理", "PyTorch", "大语言模型"], ["检索增强生成", "Docker"]),
    ("AI应用开发工程师", ["Python", "FastAPI", "大语言模型", "Docker"], ["Streamlit", "向量数据库"]),
]
COMPANIES = ["星海科技", "浦江智能", "云帆数据", "申城算法", "启明信息", "澜芯网络"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for index in range(36):
        title, required, preferred = ROLES[index % len(ROLES)]
        company = COMPANIES[index // len(ROLES)]
        jobs.append({
            "job_id": f"job_{index + 1:03d}",
            "company": company,
            "title": title + "（2027届校招）",
            "location": "上海" if index != 34 else "杭州",
            "employment_type": "校园招聘",
            "graduation_window": "2026-09至2027-08",
            "responsibilities": [f"负责{title.replace('工程师', '')}相关系统研发", "完成离线评测、性能优化和工程落地"],
            "required_skills": required,
            "preferred_skills": preferred,
            "education_requirement": "本科及以上" if index % 4 else "硕士及以上",
            "keywords": required + preferred,
            "source_url": f"https://example.com/campus/{index + 1}",
            "published_at": "2026-08-01",
            "deadline": "2027-01-31" if index != 35 else "2025-01-01",
            "status": "active" if index != 35 else "expired",
            "raw_text": f"2027届校园招聘，工作地点上海。负责{title}研发，要求 {'、'.join(required)}，掌握 {'、'.join(preferred)} 优先。",
        })
    resumes = [
        {"candidate_id": "eval_llm", "text": "硕士 计算机专业 上海求职\n技能：Python、PyTorch、LLM、RAG、FAISS、FastAPI、Docker\n项目经历\nRAG问答系统项目\n使用Python、PyTorch和FAISS实现检索增强生成，离线召回率提升12%。", "expected_skills": ["Python", "PyTorch", "大语言模型", "检索增强生成", "FAISS", "FastAPI", "Docker"]},
        {"candidate_id": "eval_mining", "text": "本科 数据科学专业 上海\n技能：Python、SQL、机器学习、数据挖掘、推荐系统\n项目经历\n商品推荐系统\n完成特征工程和推荐模型训练，nDCG提升8%。", "expected_skills": ["Python", "SQL", "机器学习", "数据挖掘", "推荐系统"]},
        {"candidate_id": "eval_nlp", "text": "硕士 人工智能专业\n技能：Python、PyTorch、NLP、深度学习、LLM\n项目经历\n中文文本分类模型\n使用PyTorch训练模型，F1达到91%。", "expected_skills": ["Python", "PyTorch", "自然语言处理", "深度学习", "大语言模型"]},
    ]
    relevance = {
        "eval_llm": {job["job_id"]: (3 if "大模型" in job["title"] else 2 if "AI应用" in job["title"] or "NLP" in job["title"] else 0) for job in jobs},
        "eval_mining": {job["job_id"]: (3 if "数据挖掘" in job["title"] else 2 if "搜索推荐" in job["title"] or "机器学习" in job["title"] else 0) for job in jobs},
        "eval_nlp": {job["job_id"]: (3 if "NLP" in job["title"] else 2 if "大模型" in job["title"] or "机器学习" in job["title"] else 0) for job in jobs},
    }
    (OUT / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "resumes.json").write_text(json.dumps(resumes, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "relevance.json").write_text(json.dumps(relevance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated {len(jobs)} jobs and {len(resumes)} synthetic resumes")


if __name__ == "__main__":
    main()
