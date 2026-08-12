from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src.models.schemas import ResumeProfile
from src.services import AnalysisService

st.set_page_config(page_title="秋招雷达 AI", page_icon="🎯", layout="wide")


@st.cache_resource
def service() -> AnalysisService:
    return AnalysisService()


def initialize_state() -> None:
    st.session_state.setdefault("resume", None)
    st.session_state.setdefault("matches", [])
    st.session_state.setdefault("selected_job_id", None)


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
    jobs = api.jobs.list_jobs()
    st.metric("岗位库数量", len(jobs))
    if jobs:
        table = [{"公司": j.company, "岗位": j.title, "地点": j.location, "状态": j.status, "截止日期": j.deadline or "未知", "技能": "、".join(j.required_skills)} for j in jobs]
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


def page_ranking(api: AnalysisService) -> None:
    st.subheader("3 · 岗位推荐")
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


def page_advice(api: AnalysisService) -> None:
    st.subheader("4 · 简历优化")
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
    st.subheader("5 · 模拟面试")
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


def main() -> None:
    initialize_state()
    render_header()
    api = service()
    page = st.sidebar.radio("工作台", ["简历解析", "岗位库", "岗位推荐", "简历优化", "模拟面试"])
    st.sidebar.caption("离线规则 + 可解释混合评分")
    if st.session_state.resume and st.sidebar.button("删除我的分析记录"):
        count = api.delete_candidate_data(st.session_state.resume.candidate_id)
        st.sidebar.success(f"已删除 {count} 条本地分析记录。")
    {"简历解析": page_resume, "岗位库": page_jobs, "岗位推荐": page_ranking, "简历优化": page_advice, "模拟面试": page_interview}[page](api)


if __name__ == "__main__":
    main()
