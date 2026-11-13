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

CANDIDATES = [
    {
        "candidate_id": "eval_llm",
        "text": "硕士 计算机专业 上海求职\n技能：Python、PyTorch、LLM、RAG、FAISS、FastAPI、Docker\n项目经历\nRAG问答系统项目\n使用Python、PyTorch和FAISS实现检索增强生成，离线召回率提升12%。",
        "expected_skills": ["Python", "PyTorch", "大语言模型", "检索增强生成", "FAISS", "FastAPI", "Docker"],
        "role_grades": {"大模型": 3, "AI应用": 2, "NLP": 2},
    },
    {
        "candidate_id": "eval_mining",
        "text": "本科 数据科学专业 上海\n技能：Python、SQL、机器学习、数据挖掘、推荐系统\n项目经历\n商品推荐系统\n完成特征工程和推荐模型训练，nDCG提升8%。",
        "expected_skills": ["Python", "SQL", "机器学习", "数据挖掘", "推荐系统"],
        "role_grades": {"数据挖掘": 3, "搜索推荐": 2, "机器学习": 2},
    },
    {
        "candidate_id": "eval_nlp",
        "text": "硕士 人工智能专业\n技能：Python、PyTorch、NLP、深度学习、LLM\n项目经历\n中文文本分类模型\n使用PyTorch训练模型，F1达到91%。",
        "expected_skills": ["Python", "PyTorch", "自然语言处理", "深度学习", "大语言模型"],
        "role_grades": {"NLP": 3, "大模型": 2, "机器学习": 2},
    },
    {
        "candidate_id": "eval_ml",
        "text": "硕士 计算机专业 上海求职\n技能：Python、PyTorch、机器学习、深度学习、SQL、Docker\n项目经历\n图像分类与模型压缩\n完成模型训练、消融实验和容器化推理，准确率达到89%。",
        "expected_skills": ["Python", "PyTorch", "机器学习", "深度学习", "SQL", "Docker"],
        "role_grades": {"机器学习": 3, "数据挖掘": 2, "搜索推荐": 2},
    },
    {
        "candidate_id": "eval_recommendation",
        "text": "本科 软件工程专业 上海\n技能：Python、SQL、推荐系统、机器学习、PyTorch\n项目经历\n短视频推荐实验\n实现召回、特征工程与排序模型，离线nDCG提升6%。",
        "expected_skills": ["Python", "SQL", "推荐系统", "机器学习", "PyTorch"],
        "role_grades": {"搜索推荐": 3, "数据挖掘": 2},
    },
    {
        "candidate_id": "eval_ai_app",
        "text": "本科 计算机专业 上海求职\n技能：Python、FastAPI、LLM、Docker、Streamlit、向量数据库\n项目经历\n企业知识库助手\n实现接口服务、向量检索、可视化页面和Docker部署。",
        "expected_skills": ["Python", "FastAPI", "大语言模型", "Docker", "Streamlit", "向量数据库"],
        "role_grades": {"AI应用": 3, "大模型": 2},
    },
    {
        "candidate_id": "eval_rag_backend",
        "text": "硕士 软件工程专业 上海\n技能：Python、RAG、FAISS、FastAPI、Docker、LLM\n项目经历\n检索服务后端\n使用FAISS与FastAPI构建混合检索接口，完成离线召回评测和容器化部署。",
        "expected_skills": ["Python", "检索增强生成", "FAISS", "FastAPI", "Docker", "大语言模型"],
        "role_grades": {"大模型": 3, "AI应用": 2},
    },
    {
        "candidate_id": "eval_nlp_engineering",
        "text": "硕士 人工智能专业 上海求职\n技能：Python、PyTorch、NLP、Transformer、FastAPI、Docker\n项目经历\n文本审核服务\n训练Transformer分类器并封装推理接口，宏平均F1达到88%。",
        "expected_skills": ["Python", "PyTorch", "自然语言处理", "Transformer", "FastAPI", "Docker"],
        "role_grades": {"NLP": 3, "机器学习": 2, "AI应用": 2},
    },
    {
        "candidate_id": "eval_cv_transfer",
        "text": "本科 自动化专业 上海\n技能：Python、PyTorch、深度学习、OpenCV、目标检测\n项目经历\n工业缺陷检测\n训练目标检测模型并完成数据增强和误差分析。",
        "expected_skills": ["Python", "PyTorch", "深度学习", "OpenCV", "目标检测"],
        "role_grades": {"机器学习": 2},
    },
    {
        "candidate_id": "eval_data_analyst",
        "text": "本科 统计学专业 上海求职\n技能：Python、SQL、机器学习、数据挖掘、XGBoost\n项目经历\n用户流失预测\n完成数据清洗、特征工程、XGBoost建模和误差分析。",
        "expected_skills": ["Python", "SQL", "机器学习", "数据挖掘", "XGBoost"],
        "role_grades": {"数据挖掘": 3, "机器学习": 2},
    },
    {
        "candidate_id": "eval_mlops",
        "text": "硕士 计算机专业 上海\n技能：Python、Docker、Linux、FastAPI、机器学习、模型部署\n项目经历\n模型推理平台\n实现模型版本管理、批量推理接口和容器化部署。",
        "expected_skills": ["Python", "Docker", "Linux", "FastAPI", "机器学习", "模型部署"],
        "role_grades": {"AI应用": 2, "机器学习": 2},
    },
    {
        "candidate_id": "eval_search_ads",
        "text": "硕士 数据科学专业 上海求职\n技能：Python、SQL、机器学习、推荐系统、Learning to Rank\n项目经历\n搜索排序实验\n构建点击率特征与排序模型，完成离线MRR和nDCG评测。",
        "expected_skills": ["Python", "SQL", "机器学习", "推荐系统", "Learning to Rank"],
        "role_grades": {"搜索推荐": 3, "数据挖掘": 2, "机器学习": 2},
    },
]


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
        {key: value for key, value in candidate.items() if key != "role_grades"}
        for candidate in CANDIDATES
    ]
    relevance = {
        candidate["candidate_id"]: {
            job["job_id"]: max(
                (grade for role, grade in candidate["role_grades"].items() if role in job["title"]),
                default=0,
            )
            for job in jobs
        }
        for candidate in CANDIDATES
    }
    (OUT / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "resumes.json").write_text(json.dumps(resumes, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "relevance.json").write_text(json.dumps(relevance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated {len(jobs)} jobs and {len(resumes)} synthetic resumes")


if __name__ == "__main__":
    main()
