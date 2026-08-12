from __future__ import annotations

from src.models.schemas import InterviewQuestion, JobProfile, MatchResult, ResumeProfile


def generate_questions(resume: ResumeProfile, job: JobProfile, match: MatchResult, difficulty: str = "进阶") -> list[InterviewQuestion]:
    project = resume.projects[0] if resume.projects else None
    project_name = project.name if project else "你最熟悉的项目"
    project_evidence = (project.evidence[0] if project and project.evidence else project.description if project else "简历项目经历")
    questions = [
        InterviewQuestion(
            category="简历项目深挖",
            question=f"请用三分钟介绍“{project_name}”，重点说明你负责的部分和最难的问题。",
            focus="事实边界、技术决策与个人贡献",
            answer_structure=["项目目标与约束", "本人负责的行动", "真实结果与复盘"],
            follow_ups=["如果重新做一次会改变什么？", "你如何验证结果来自你的方案？"],
            evidence=project_evidence[:300],
            difficulty=difficulty,
        ),
        InterviewQuestion(
            category="岗位知识匹配",
            question=f"该岗位要求 {('、'.join(job.required_skills[:3]) or '核心技术能力')}，请说明它们在一个完整系统中的协作方式。",
            focus="岗位必需技能的理解深度",
            answer_structure=["概念与边界", "系统中的位置", "权衡与验证方法"],
            follow_ups=["出现性能瓶颈时如何定位？", "有哪些替代方案？"],
            evidence="JD 必需技能：" + ("、".join(job.required_skills) or "岗位职责"),
            difficulty=difficulty,
        ),
        InterviewQuestion(
            category="技能缺口",
            question=f"如果入职后需要快速掌握 {match.missing_required_skills[0] if match.missing_required_skills else '一项陌生技术'}，你的两周学习与验证计划是什么？",
            focus="学习能力与诚实处理知识边界",
            answer_structure=["拆解目标", "最小实践", "验证标准与复盘"],
            follow_ups=["如何判断已经达到可用水平？"],
            evidence="匹配分析中的技能缺口",
            difficulty=difficulty,
        ),
        InterviewQuestion(
            category="系统设计",
            question="设计一个可解释的简历与岗位匹配系统，你会如何兼顾召回率、排序质量、成本和隐私？",
            focus="检索、排序、评测与工程权衡",
            answer_structure=["目标和数据流", "召回与精排", "指标、监控和隐私"],
            follow_ups=["为什么不能只让大模型给总分？", "如何做离线评测？"],
            evidence=f"目标岗位：{job.company} {job.title}",
            difficulty=difficulty,
        ),
        InterviewQuestion(
            category="行为面试",
            question="讲一次你发现原方案不可行并主动调整方向的经历。",
            focus="判断、协作和复盘能力",
            answer_structure=["情境与目标", "判断依据和行动", "结果与反思"],
            follow_ups=["当时谁不同意？你如何推进？"],
            evidence="基于候选人真实经历作答，不应补造案例",
            difficulty=difficulty,
        ),
    ]
    return questions
