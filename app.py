from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote, urlparse

import pandas as pd
import streamlit as st

from src.agents import JobAgentPreferences
from src.models.schemas import ResumeProfile
from src.services import AnalysisService
from src.ui.demo_presenters import (
    embedding_benchmark_rows,
    embedding_status_rows,
    fusion_tuning_rows,
    fusion_tuning_summary,
    job_status_summary,
    job_table_rows,
    is_official_source,
    ranking_comparison_rows,
    source_badge,
)


ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="秋招雷达 AI", page_icon="🎯", layout="wide")


@st.cache_resource
def service() -> AnalysisService:
    return AnalysisService()


def initialize_state() -> None:
    st.session_state.setdefault("resume", None)
    st.session_state.setdefault("matches", [])
    st.session_state.setdefault("selected_job_id", None)
    st.session_state.setdefault("job_agent_result", None)


def _safe_source_url(source_url: str) -> str:
    """Return a Markdown-safe HTTP(S) source URL, or an empty string."""
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    return quote(source_url, safe=":/?#[]@!$&'*+,;=%")


def render_header() -> None:
    st.title("🎯 秋招雷达 AI")
    st.caption("上海 AI / 算法 / 数据岗位的可解释匹配、真实简历优化与面试准备")
    st.info("隐私提示：默认仅在本机 SQLite 保存分析摘要；不记录完整简历。启用外部模型前请自行确认数据处理方式。", icon="🔒")


def page_resume(api: AnalysisService) -> None:
    st.subheader("1 · 简历解析")
    uploaded = st.file_uploader("上传 PDF、DOCX、TXT 或 Markdown 简历", type=["pdf", "docx", "txt", "md", "markdown"])
    if uploaded and st.button("解析简历", type="primary", use_container_width=True):
        try:
            st.session_state.resume = api.parse_resume_file(uploaded.name, uploaded.getvalue())
            st.session_state.matches = []
            st.success("解析完成，请检查并修正结构化字段。")
        except Exception as exc:
            st.error(str(exc))
    resume = st.session_state.resume
    if resume:
        col1, col2 = st.columns(2)
        with col1:
            skills = st.text_area("技能（每行一个）", "\n".join(resume.skills), height=180)
            roles = st.text_input("目标方向（逗号分隔）", ", ".join(resume.preferred_roles))
        with col2:
            st.text_area("原文预览", resume.raw_text[:6000], height=250, disabled=True)
        if st.button("确认修改"):
            payload = resume.model_dump()
            payload["skills"] = [line.strip() for line in skills.splitlines() if line.strip()]
            payload["preferred_roles"] = [item.strip() for item in roles.replace("，", ",").split(",") if item.strip()]
            st.session_state.resume = ResumeProfile.model_validate(payload)
            st.success("结构化信息已更新。")


def page_jobs(api: AnalysisService) -> None:
    st.subheader("2 · 岗位库")
    st.markdown("#### 官方公开 JD 演示库")
    st.caption("数据来自已核验的官方招聘页面；导入过程只读取仓库内的数据集，不访问外部网站。")
    if st.button("一键加载 30 条官方 JD", type="primary", use_container_width=True):
        count, statuses = api.import_verified_jobs()
        st.success(
            f"已导入或更新 {count} 条官方 JD："
            f"在招 {statuses['active']}、过期 {statuses['expired']}、待确认 {statuses['unknown']}。"
        )

    jobs = api.jobs.list_jobs()
    official_jobs = [job for job in jobs if is_official_source(job)]
    summary = job_status_summary(official_jobs)
    metric_columns = st.columns(4)
    for column, (label, value) in zip(metric_columns, summary.items()):
        column.metric(label, value)

    if official_jobs:
        filter_left, filter_right = st.columns(2)
        companies = sorted({job.company for job in official_jobs})
        selected_companies = filter_left.multiselect("公司筛选", companies)
        status_options = {"在招": "active", "过期": "expired", "待确认": "unknown"}
        selected_status_labels = filter_right.multiselect("状态筛选", list(status_options))
        selected_statuses = {status_options[label] for label in selected_status_labels}
        filtered_jobs = [
            job
            for job in official_jobs
            if (not selected_companies or job.company in selected_companies)
            and (not selected_statuses or job.status in selected_statuses)
        ]
        st.dataframe(
            pd.DataFrame(job_table_rows(filtered_jobs)),
            use_container_width=True,
            hide_index=True,
            column_config={
                "官方来源": st.column_config.LinkColumn(
                    "官方来源",
                    display_text="打开官方 JD",
                )
            },
        )

    st.divider()
    st.markdown("#### 导入自己的岗位")
    left, right = st.columns(2)
    with left:
        file = st.file_uploader("批量导入 CSV / JSON", type=["csv", "json"])
        if file and st.button("导入岗位文件", type="primary"):
            count, errors = api.import_jobs(file.name, file.getvalue())
            st.success(f"成功导入或更新 {count} 条岗位。")
            if errors:
                st.warning("\n".join(errors))
    with right:
        company = st.text_input("公司", "用户导入")
        title = st.text_input("岗位名称", "AI 应用工程师（校招）")
        pasted = st.text_area("粘贴一条 JD", height=140)
        if pasted and st.button("添加粘贴岗位"):
            api.add_pasted_job(pasted, title, company)
            st.success("岗位已加入本地岗位库。")


def page_ranking(api: AnalysisService) -> None:
    st.subheader("3 · 岗位推荐")
    render_embedding_status(api)
    if not st.session_state.resume:
        st.warning("请先在“简历解析”页上传并确认简历。")
        return
    top_k = st.slider("返回岗位数", 1, 20, 5)
    include_expired = st.toggle("显示已截止岗位", False)
    if st.button("开始匹配", type="primary", use_container_width=True):
        st.session_state.matches = api.rank(st.session_state.resume, top_k, include_expired)
    matches = st.session_state.matches
    if not matches:
        st.caption("尚无结果。请确认岗位库内有上海校招 AI / 算法 / 数据岗位。")
        return
    jobs = {j.job_id: j for j in api.jobs.list_jobs()}
    for index, match in enumerate(matches, 1):
        job = jobs[match.job_id]
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 2, 2])
            c1.markdown(f"### {index}. {job.company} · {job.title}")
            c1.caption(f"{job.location}｜{match.recommendation}")
            c1.caption(source_badge(job))
            source_url = _safe_source_url(job.source_url)
            if source_url:
                c1.markdown(f"[查看岗位来源]({source_url})")
            c2.metric("匹配分", f"{match.total_score:.1f}")
            if c3.button("查看详情", key=f"detail-{job.job_id}"):
                st.session_state.selected_job_id = job.job_id
            st.progress(match.total_score / 100)
            st.write("命中：", "、".join(match.matched_skills) or "暂无")
            st.write("缺失硬技能：", "、".join(match.missing_required_skills) or "无")
            with st.expander("分项评分与证据"):
                st.json(match.subscores.model_dump())
                for item in match.evidence:
                    st.markdown(f"- {item}")


def _selected(api: AnalysisService):
    job_id = st.session_state.selected_job_id
    return next((m for m in st.session_state.matches if m.job_id == job_id), None)


def page_job_agent(api: AnalysisService) -> None:
    st.subheader("4 · 求职决策 Agent")
    st.caption(
        "受约束 Agent 根据状态选择岗位搜索、资格过滤、六维排序和匹配解释工具；"
        "硬条件不会被自动放宽。"
    )
    render_embedding_status(api)
    if not st.session_state.resume:
        st.warning("请先在“简历解析”页上传并确认简历。")
        return

    left, right = st.columns(2)
    location = left.text_input("目标城市", "上海", key="agent-location")
    role_text = right.text_input(
        "目标岗位方向（逗号分隔）",
        "、".join(st.session_state.resume.preferred_roles),
        key="agent-roles",
    )
    top_k = st.slider("返回岗位数", 1, 20, 5, key="agent-top-k")
    explain = st.toggle("同时解释 Top-1 匹配依据", True, key="agent-explain")
    if st.button("运行求职决策 Agent", type="primary", use_container_width=True):
        roles = [
            item.strip()
            for item in role_text.replace("，", ",").replace("、", ",").split(",")
            if item.strip()
        ]
        st.session_state.job_agent_result = api.run_job_agent(
            st.session_state.resume,
            JobAgentPreferences(
                location=location,
                target_roles=roles,
                top_k=top_k,
                explain_top_job=explain,
            ),
        )

    result = st.session_state.job_agent_result
    if result is None:
        st.info("运行后可查看真实工具调用顺序、参数摘要、耗时和停止原因。")
        return
    if result.status == "completed":
        st.success(result.message)
    elif result.status == "needs_clarification":
        st.warning(result.message)
        for question in result.clarification_questions:
            st.write(f"- {question}")
    else:
        st.error(result.message)

    status_columns = st.columns(4)
    status_columns[0].metric("停止原因", result.stop_reason)
    status_columns[1].metric("工具调用", len(result.trace))
    status_columns[2].metric("实际后端", result.actual_backend)
    status_columns[3].metric("发生回退", "是" if result.fallback_occurred else "否")
    if result.matches:
        jobs = {job.job_id: job for job in api.jobs.list_jobs()}
        rows = [
            {
                "公司": jobs[match.job_id].company,
                "岗位": jobs[match.job_id].title,
                "总分": match.total_score,
                "建议": match.recommendation,
            }
            for match in result.matches
            if match.job_id in jobs
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if result.explanation:
        st.info(result.explanation)
    st.markdown("#### Tool Trace")
    st.dataframe(
        pd.DataFrame([step.model_dump() for step in result.trace]),
        use_container_width=True,
        hide_index=True,
    )


def page_advice(api: AnalysisService) -> None:
    st.subheader("5 · 简历优化")
    match = _selected(api)
    if not match:
        st.warning("请先在“岗位推荐”页选择一个岗位。")
        return
    detail = api.build_detail(st.session_state.resume, match.job_id, match)
    st.markdown(f"### {detail['job'].company} · {detail['job'].title}")
    for item in detail["advice"].items:
        icon = "✅" if item.action == "可直接修改" else "🧪"
        with st.container(border=True):
            st.markdown(f"**{icon} {item.category}｜{item.action}**")
            st.write(item.suggestion)
            st.caption("依据：" + item.evidence)
    st.download_button("下载完整 Markdown 报告", detail["report"], file_name=f"{match.job_id}-analysis.md", mime="text/markdown", use_container_width=True)


def page_interview(api: AnalysisService) -> None:
    st.subheader("6 · 模拟面试")
    match = _selected(api)
    if not match:
        st.warning("请先在“岗位推荐”页选择一个岗位。")
        return
    difficulty = st.segmented_control("难度", ["基础", "进阶", "挑战"], default="进阶")
    detail = api.build_detail(st.session_state.resume, match.job_id, match, difficulty)
    for index, question in enumerate(detail["questions"], 1):
        with st.expander(f"{index}. [{question.category}] {question.question}", expanded=index == 1):
            st.write("**考察点：**", question.focus)
            st.write("**回答结构：**", " → ".join(question.answer_structure))
            st.write("**可能追问：**", "；".join(question.follow_ups))
            st.caption("关联依据：" + question.evidence)
            st.text_area("练习回答", key=f"answer-{match.job_id}-{index}", height=120)


def page_evaluation(api: AnalysisService) -> None:
    st.subheader("7 · 实验看板")
    st.info("双模型独立盲标与裁决形成的模型辅助评测基准")
    render_embedding_status(api)

    try:
        result = api.load_real_evaluation()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        st.error(f"真实评测结果读取失败：{exc}")
        return

    agreement_path = ROOT / "data" / "real_jobs" / "annotation_agreement.json"
    try:
        agreement = json.loads(agreement_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        st.error(f"一致性数据读取失败：{exc}")
        return

    try:
        dataset = result["dataset"]
        agreement_dataset = agreement["dataset"]
        overall = agreement["overall"]
        disagreements = agreement["disagreements"]
        disclosure_columns = st.columns(4)
        disclosure_columns[0].metric("官方 JD", agreement_dataset["jobs"])
        disclosure_columns[1].metric("在招岗位", dataset["active_jobs"])
        disclosure_columns[2].metric("合成候选人", dataset["candidates"])
        disclosure_columns[3].metric("human_gold", str(dataset["human_gold"]).lower())

        st.markdown("#### 标注一致性")
        agreement_columns = st.columns(4)
        agreement_columns[0].metric("精确一致率", f"{overall['exact_agreement']:.2%}")
        agreement_columns[1].metric("二次加权 κ", f"{overall['quadratic_weighted_kappa']:.4f}")
        agreement_columns[2].metric("分歧", disagreements["count"])
        agreement_columns[3].metric("严重分歧", disagreements["severe_count"])

        st.markdown("#### 排序方法比较")
        st.dataframe(
            pd.DataFrame(ranking_comparison_rows(result)),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Embedding 后端实测对比")
        bge_path = ROOT / "data" / "real_jobs" / "evaluation_results_bge_m3.json"
        try:
            bge_result = json.loads(bge_path.read_text(encoding="utf-8"))
            st.dataframe(
                pd.DataFrame(embedding_benchmark_rows(result, bge_result)),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("仅呈现当前数据集的实测差值；结果不代表 BGE-M3 在所有任务上全面提升。")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            st.caption(f"BGE-M3 对比结果暂不可用：{exc}")

        st.markdown("#### 融合权重探索")
        tuning_path = ROOT / "data" / "real_jobs" / "fusion_weight_search_bge_m3.json"
        try:
            tuning_result = json.loads(tuning_path.read_text(encoding="utf-8"))
            tuning_rows = fusion_tuning_rows(tuning_result)
            tuning_summary = fusion_tuning_summary(tuning_result)
            st.dataframe(pd.DataFrame(tuning_rows), use_container_width=True, hide_index=True)
            summary_columns = st.columns(3)
            fold_range = tuning_summary["fold_ndcg5_range"]
            summary_columns[0].metric("配置更新决定", tuning_summary["promotion"])
            summary_columns[1].metric("三折 nDCG@5 范围", f"{fold_range[0]:.4f}–{fold_range[1]:.4f}")
            summary_columns[2].metric("不同折权重方案数", tuning_summary["unique_fold_winners"])
            stability = "稳定" if tuning_summary["stable_across_all_folds"] else "不稳定"
            st.caption(f"折间权重稳定性：{stability}")
            for reason in tuning_summary["failure_reasons"]:
                st.warning(f"配置更新拒绝原因：{reason}")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            st.caption(f"融合权重探索结果暂不可用：{exc}")

        st.markdown("#### 局限性")
        limitations = result.get("limitations", [])
        if len(limitations) != 3:
            raise ValueError("评测结果必须披露三条局限性")
        for limitation in limitations:
            st.warning(limitation)
    except (KeyError, TypeError, ValueError) as exc:
        st.error(f"实验看板数据格式错误：{exc}")


def render_embedding_status(api: AnalysisService) -> None:
    """Disclose configured and actually selected embedding backend."""
    rows = embedding_status_rows(api.embedding_status, api.settings.embedding_model)
    with st.expander("Embedding 运行状态", expanded=False):
        columns = st.columns(4)
        for column, (label, value) in zip(columns, rows.items()):
            column.metric(label, value)
        if rows["回退"] == "是":
            st.warning("BGE-M3 不可用，当前已回退到本地 hashing。")


def main() -> None:
    initialize_state()
    render_header()
    api = service()
    page = st.sidebar.radio(
        "工作台",
        ["简历解析", "岗位库", "岗位推荐", "求职决策 Agent", "简历优化", "模拟面试", "实验看板"],
    )
    st.sidebar.caption("受约束 Agent + 确定性资格过滤与可解释混合评分")
    if st.session_state.resume and st.sidebar.button("删除我的分析记录"):
        count = api.delete_candidate_data(st.session_state.resume.candidate_id)
        st.sidebar.success(f"已删除 {count} 条本地分析记录。")
    {
        "简历解析": page_resume,
        "岗位库": page_jobs,
        "岗位推荐": page_ranking,
        "求职决策 Agent": page_job_agent,
        "简历优化": page_advice,
        "模拟面试": page_interview,
        "实验看板": page_evaluation,
    }[page](api)


if __name__ == "__main__":
    main()
