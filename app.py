from __future__ import annotations

import os
import html
from collections import Counter
from datetime import datetime
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.auth_ui import inject_oauth_hash_bridge, show_login_ui
from utils.cv_processor import AdvancedCVProcessor
from utils.field_config import get_all_fields, get_default_weights
from utils.rag_engine import AdvancedRAGEngine
from utils.supabase_client import (
    complete_oauth_from_tokens,
    get_current_company_name,
    get_current_user_email,
    get_current_user_id,
    hydrate_session_from_supabase,
    sign_out,
)

st.set_page_config(
    page_title="TalentHire Pro",
    page_icon="TH",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_oauth_hash_bridge()


def qp_value(name: str, default: str = "") -> str:
    value = st.query_params.get(name, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value or default


if qp_value("access_token"):
    result = complete_oauth_from_tokens(qp_value("access_token"), qp_value("refresh_token"))
    st.query_params.clear()
    if result.get("success"):
        st.rerun()
    st.error(result.get("error", "Google authentication failed."))
    st.stop()

hydrate_session_from_supabase()
if not get_current_user_id():
    show_login_ui()
    st.stop()


st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
      * { font-family: 'Inter', sans-serif; }
      html, body, [data-testid="stAppViewContainer"] { background: #0b0d12; color: #f4f4f5; }
      [data-testid="stHeader"] { background: rgba(11,13,18,.72); backdrop-filter: blur(18px); }
      [data-testid="stSidebar"] { background: #0f1117; border-right: 1px solid rgba(255,255,255,.08); }
      [data-testid="stSidebar"] * { color: #e5e7eb; }
      .block-container { padding-top: 1.4rem; max-width: 1480px; }
      .app-logo {
        width: 54px; height: 54px; border-radius: 17px; display: grid; place-items: center;
        color: #fff; font-weight: 900; letter-spacing: -.08em;
        border: 1px solid rgba(255,255,255,.16);
        background: linear-gradient(145deg, #050505 0%, #262626 50%, #ffffff 51%, #cfcfcf 100%);
        box-shadow: 0 18px 42px rgba(0,0,0,.35);
      }
      .hero {
        border: 1px solid rgba(255,255,255,.10); border-radius: 30px; padding: 2rem;
        background: radial-gradient(circle at 12% 0%, rgba(255,255,255,.12), transparent 32%),
                    linear-gradient(135deg, rgba(255,255,255,.07), rgba(255,255,255,.025));
        box-shadow: 0 28px 90px rgba(0,0,0,.34); margin-bottom: 1.2rem;
      }
      .hero h1 { font-size: clamp(2.1rem, 4vw, 4.1rem); line-height: .96; letter-spacing: -.07em; margin: .55rem 0 .75rem; color:#fff; }
      .hero p { color: #a8afbd; font-size: 1.02rem; max-width: 760px; line-height: 1.65; margin: 0; }
      .chip-row { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.1rem; }
      .chip { border: 1px solid rgba(255,255,255,.11); border-radius: 999px; color:#d7dbe4; padding:.42rem .75rem; background:rgba(255,255,255,.035); font-size:.85rem; }
      .metric-card, .panel-card {
        border: 1px solid rgba(255,255,255,.10); border-radius: 22px; background: rgba(255,255,255,.045);
        padding: 1.1rem; box-shadow: 0 18px 48px rgba(0,0,0,.22);
      }
      .metric-label { color:#8f97a8; font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; font-weight:700; }
      .metric-value { color:#fff; font-size:2rem; font-weight:850; margin-top:.35rem; letter-spacing:-.045em; }
      .metric-help { color:#a5adbb; font-size:.82rem; margin-top:.25rem; }
      .section-title { font-size:1.25rem; font-weight:800; letter-spacing:-.03em; color:#fff; margin:.4rem 0 .35rem; }
      .muted { color:#9ca3af; }
      .candidate-card {
        border: 1px solid rgba(255,255,255,.10); border-radius: 20px; padding:1rem; margin:.7rem 0;
        background: linear-gradient(135deg, rgba(255,255,255,.06), rgba(255,255,255,.025));
      }
      .candidate-title { font-size:1.08rem; color:#fff; font-weight:800; }
      .candidate-meta { color:#a8afbd; font-size:.9rem; margin-top:.25rem; }
      .score-pill { display:inline-block; padding:.25rem .6rem; border-radius:999px; background:#fff; color:#111; font-weight:800; font-size:.82rem; }
      .sidebar-brand { text-align:left; padding:.5rem .2rem 1rem; }
      .sidebar-brand h2 { margin:.7rem 0 .15rem; font-size:1.25rem; letter-spacing:-.04em; color:#fff; }
      .sidebar-brand p { margin:0; color:#9ca3af; font-size:.86rem; }
      div[data-testid="stTabs"] button { color:#d9dde7; }
      .stButton button, .stDownloadButton button { border-radius: 12px !important; font-weight: 700 !important; }
      .stTextInput input, .stTextArea textarea { border-radius: 14px !important; }
      hr { border-color: rgba(255,255,255,.10); }
    </style>
    """,
    unsafe_allow_html=True,
)


def clamp_score(score: float) -> float:
    try:
        value = float(score)
    except Exception:
        value = 0.0
    if value <= 1.0:
        value *= 100.0
    return min(max(value, 0.0), 100.0)


def candidate_key(candidate: Dict) -> str:
    return f"{candidate.get('filename','')}::{candidate.get('email','')}::{candidate.get('name','')}"


def cvs_to_dataframe(cvs: List[Dict]) -> pd.DataFrame:
    rows = []
    for cv in cvs:
        rows.append({
            "Name": cv.get("name", ""),
            "Email": cv.get("email", ""),
            "Phone": cv.get("phone", ""),
            "Location": cv.get("location", ""),
            "Experience Years": round(float(cv.get("years_of_experience", 0) or 0), 1),
            "Experience Level": cv.get("experience_level", ""),
            "Education Level": cv.get("education_level", ""),
            "Industry": cv.get("field", ""),
            "Skills": ", ".join(cv.get("skills", [])[:20]),
            "Score Percent": round(clamp_score(cv.get("final_score", 0)), 1) if "final_score" in cv else "",
            "Match Reason": cv.get("match_reason", ""),
            "File": cv.get("filename", ""),
        })
    return pd.DataFrame(rows)


def normalized_weights(raw: Dict[str, int]) -> Dict[str, float]:
    total = sum(raw.values()) or 1
    return {key: value / total for key, value in raw.items()}


def render_metric(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{html.escape(label)}</div>
          <div class="metric-value">{html.escape(str(value))}</div>
          <div class="metric-help">{html.escape(help_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_candidate(candidate: Dict, index: int, allow_favorite: bool = True) -> None:
    score = clamp_score(candidate.get("final_score", 0))
    skills = candidate.get("skills", []) or []
    with st.container(border=True):
        cols = st.columns([3.2, 1, 1])
        with cols[0]:
            st.markdown(f"**{index}. {candidate.get('name', 'Candidate')}**")
            st.caption(
                f"{candidate.get('experience_level', 'Unknown')} | "
                f"{float(candidate.get('years_of_experience', 0) or 0):.1f} years | "
                f"{candidate.get('location', 'Not specified')}"
            )
        with cols[1]:
            st.metric("Score", f"{score:.1f}%")
        with cols[2]:
            st.metric("Skills", len(skills))

        st.write(candidate.get("match_reason") or candidate.get("summary") or "No explanation available.")
        if skills:
            st.caption("Skills: " + ", ".join(skills[:18]))

        details = st.expander("Candidate details")
        with details:
            d1, d2, d3 = st.columns(3)
            d1.write(f"Email: {candidate.get('email', 'Not provided')}")
            d2.write(f"Phone: {candidate.get('phone', 'Not provided')}")
            d3.write(f"File: {candidate.get('filename', 'Not available')}")
            st.write(f"Education: {candidate.get('education_level', 'Not specified')}")
            st.write(f"LinkedIn: {candidate.get('linkedin', 'Not provided')}")
            st.write(f"GitHub: {candidate.get('github', 'Not provided')}")

        if allow_favorite:
            fav_keys = st.session_state.setdefault("favorite_keys", set())
            key = candidate_key(candidate)
            if key in fav_keys:
                st.caption("Shortlisted")
            elif st.button("Add to shortlist", key=f"fav_{index}_{key}"):
                st.session_state.setdefault("favorites", []).append(candidate)
                fav_keys.add(key)
                st.rerun()


user_id = get_current_user_id() or "default"
if st.session_state.get("engine_user_id") != user_id or "engine" not in st.session_state:
    with st.spinner("Loading recruitment engine..."):
        st.session_state.engine = AdvancedRAGEngine(
            model_name="all-mpnet-base-v2",
            use_reranker=True,
            session_id=user_id,
        )
        st.session_state.engine_user_id = user_id
        st.session_state.setdefault("processed_cvs", [])
        st.session_state.setdefault("search_results", [])
        st.session_state.setdefault("favorites", [])
        st.session_state.setdefault("favorite_keys", set())

engine = st.session_state.engine
all_fields = get_all_fields()
if "selected_field" not in st.session_state or st.session_state.selected_field not in all_fields:
    st.session_state.selected_field = "Software Engineering" if "Software Engineering" in all_fields else all_fields[0]

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
          <div class="app-logo">TH</div>
          <h2>TalentHire Pro</h2>
          <p>AI CV screening workspace</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("Signed in")
    st.write(get_current_company_name())
    st.caption(get_current_user_email() or "")
    st.divider()

    selected_field = st.selectbox("Industry", all_fields, index=all_fields.index(st.session_state.selected_field))
    st.session_state.selected_field = selected_field

    defaults = get_default_weights(selected_field)
    default_weights = {
        "education": int(defaults.get("education", 20)),
        "experience": int(defaults.get("experience", 30)),
        "skills": int(defaults.get("skills", 30)),
        "projects": int(defaults.get("projects", 10)),
        "certifications": int(defaults.get("certifications", 10)),
    }
    st.markdown("#### Scoring weights")
    w_edu = st.slider("Education", 0, 100, default_weights["education"], 5)
    w_exp = st.slider("Experience", 0, 100, default_weights["experience"], 5)
    w_ski = st.slider("Skills", 0, 100, default_weights["skills"], 5)
    w_pro = st.slider("Projects", 0, 100, default_weights["projects"], 5)
    w_cer = st.slider("Certifications", 0, 100, default_weights["certifications"], 5)
    raw_weights = {"education": w_edu, "experience": w_exp, "skills": w_ski, "projects": w_pro, "certifications": w_cer}
    weights = normalized_weights(raw_weights)
    st.caption(f"Total weight: {sum(raw_weights.values())}%. Scores are normalized automatically.")

    st.divider()
    if st.button("Clear my CV database", use_container_width=True):
        engine.clear_database()
        st.session_state.processed_cvs = []
        st.session_state.search_results = []
        st.session_state.favorites = []
        st.session_state.favorite_keys = set()
        st.rerun()

    if st.button("Sign out", use_container_width=True):
        sign_out()
        st.rerun()

stats = engine.get_statistics() if engine else {"total_cvs": 0}
total_cvs = int(stats.get("total_cvs", 0) or 0)
avg_exp = float(stats.get("avg_experience_years", 0) or 0)

st.markdown(
    f"""
    <section class="hero">
      <div class="app-logo">TH</div>
      <h1>Professional CV screening, without the messy workflow.</h1>
      <p>Upload resumes, extract structured candidate profiles, search with job descriptions, tune scoring weights, and export shortlists from a private authenticated workspace.</p>
      <div class="chip-row">
        <span class="chip">User-isolated database</span>
        <span class="chip">Google and email sign-in</span>
        <span class="chip">Semantic search</span>
        <span class="chip">Weighted ranking</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    render_metric("Total CVs", str(total_cvs), "Current workspace")
with m2:
    render_metric("Average experience", f"{avg_exp:.1f} yrs", "Across uploaded CVs")
with m3:
    render_metric("Industries", str(len(all_fields)), "Configured scoring profiles")
with m4:
    render_metric("Model", "mpnet-v2", "Semantic embeddings")

upload_tab, search_tab, analytics_tab, all_tab, shortlist_tab, help_tab = st.tabs(
    ["Upload", "Search", "Analytics", "All CVs", "Shortlist", "Help"]
)

with upload_tab:
    st.markdown('<div class="section-title">Upload candidate CVs</div>', unsafe_allow_html=True)
    st.caption("Supported formats: PDF, DOCX, TXT. Keep files clean and text-readable for best extraction accuracy.")
    uploaded_files = st.file_uploader(
        "CV files",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.write(f"Selected files: {len(uploaded_files)}")

    if uploaded_files and st.button("Process CVs", use_container_width=True, type="primary"):
        processor = AdvancedCVProcessor(field=selected_field)
        os.makedirs("data/cvs", exist_ok=True)
        progress_bar = st.progress(0)
        status = st.empty()
        processed = 0
        errors = []

        for idx, file in enumerate(uploaded_files):
            status.write(f"Processing {idx + 1}/{len(uploaded_files)}: {file.name}")
            try:
                safe_name = os.path.basename(file.name).replace("/", "_").replace("\\", "_")
                path = os.path.join("data", "cvs", safe_name)
                with open(path, "wb") as handle:
                    handle.write(file.getbuffer())
                cv_data = processor.process(path, safe_name, field=selected_field)
                engine.add_cv(cv_data, field=selected_field)
                st.session_state.processed_cvs.append(cv_data)
                processed += 1
            except Exception as exc:
                errors.append(f"{file.name}: {exc}")
            progress_bar.progress((idx + 1) / len(uploaded_files))

        status.empty()
        progress_bar.empty()
        if processed:
            st.success(f"Processed {processed} CV file(s).")
        if errors:
            with st.expander("Files that failed"):
                for error in errors:
                    st.error(error)
        st.rerun()

with search_tab:
    st.markdown('<div class="section-title">Search candidates</div>', unsafe_allow_html=True)
    if total_cvs == 0:
        st.info("Upload CVs before running search.")
    else:
        q_col, opt_col = st.columns([3, 1])
        with q_col:
            query = st.text_area(
                "Job description or hiring criteria",
                height=150,
                placeholder="Example: Senior Python engineer with FastAPI, PostgreSQL, Docker, cloud deployment, and 4+ years of experience.",
            )
        with opt_col:
            top_k = int(st.number_input("Max results", min_value=1, max_value=50, value=10, step=1))
            use_rerank = st.checkbox("Use re-ranking", value=True)
            min_score = st.slider("Minimum score", 0, 100, 0, 5)

        if st.button("Search candidates", use_container_width=True, type="primary"):
            if not query.strip():
                st.error("Enter a job description or search criteria.")
            else:
                with st.spinner("Scoring candidates..."):
                    results = engine.search_with_weights(
                        query=query.strip(),
                        field=selected_field,
                        weights=weights,
                        top_k=top_k,
                        use_reranking=use_rerank,
                    )
                st.session_state.search_results = [r for r in results if clamp_score(r.get("final_score", 0)) >= min_score]

        results = st.session_state.get("search_results", [])
        if results:
            st.success(f"Found {len(results)} candidate(s).")
            df_results = cvs_to_dataframe(results)
            st.download_button(
                "Export search CSV",
                df_results.to_csv(index=False).encode("utf-8"),
                f"search_results_{datetime.now():%Y%m%d_%H%M%S}.csv",
                "text/csv",
                use_container_width=True,
            )
            for idx, candidate in enumerate(results, 1):
                render_candidate(candidate, idx, allow_favorite=True)
        elif st.session_state.get("search_results") == [] and total_cvs > 0:
            st.caption("No active search results yet.")

with analytics_tab:
    st.markdown('<div class="section-title">Analytics dashboard</div>', unsafe_allow_html=True)
    if total_cvs == 0:
        st.info("Upload CVs to generate analytics.")
    else:
        a1, a2, a3 = st.columns(3)
        with a1:
            st.metric("Total CVs", total_cvs)
        with a2:
            st.metric("Average experience", f"{avg_exp:.1f} years")
        with a3:
            st.metric("Active industry", selected_field)

        c1, c2 = st.columns(2)
        with c1:
            by_field = stats.get("by_field", {}) or {}
            if by_field:
                fig = px.pie(names=list(by_field.keys()), values=list(by_field.values()), title="CVs by industry", template="plotly_dark", hole=.45)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            by_level = stats.get("by_experience_level", {}) or {}
            if by_level:
                fig = px.bar(x=list(by_level.keys()), y=list(by_level.values()), title="CVs by experience level", template="plotly_dark")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Level", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True)

        all_cvs_for_skills = engine.get_all_cvs()
        skills_counter = Counter(skill for cv in all_cvs_for_skills for skill in (cv.get("skills") or []))
        if skills_counter:
            top_skills = skills_counter.most_common(15)
            fig = px.bar(x=[x[0] for x in top_skills], y=[x[1] for x in top_skills], title="Top extracted skills", template="plotly_dark")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Skill", yaxis_title="Mentions")
            st.plotly_chart(fig, use_container_width=True)

with all_tab:
    st.markdown('<div class="section-title">All CVs</div>', unsafe_allow_html=True)
    if total_cvs == 0:
        st.info("No CVs uploaded yet.")
    else:
        f_col, s_col = st.columns(2)
        with f_col:
            filter_field = st.selectbox("Filter by industry", ["All"] + all_fields, key="filter_field")
        with s_col:
            sort_by = st.selectbox("Sort by", ["Name A-Z", "Experience high-low", "Experience low-high"], key="sort_by")

        field_arg = None if filter_field == "All" else filter_field
        all_cvs = engine.get_all_cvs(field=field_arg)
        if sort_by == "Experience high-low":
            all_cvs.sort(key=lambda item: float(item.get("years_of_experience", 0) or 0), reverse=True)
        elif sort_by == "Experience low-high":
            all_cvs.sort(key=lambda item: float(item.get("years_of_experience", 0) or 0))
        else:
            all_cvs.sort(key=lambda item: (item.get("name") or "").lower())

        st.download_button(
            "Export all CVs CSV",
            cvs_to_dataframe(all_cvs).to_csv(index=False).encode("utf-8"),
            f"all_cvs_{datetime.now():%Y%m%d}.csv",
            "text/csv",
            use_container_width=True,
        )
        for idx, candidate in enumerate(all_cvs, 1):
            render_candidate(candidate, idx, allow_favorite=True)

with shortlist_tab:
    st.markdown('<div class="section-title">Shortlisted candidates</div>', unsafe_allow_html=True)
    favorites = st.session_state.get("favorites", [])
    if not favorites:
        st.info("No shortlisted candidates yet. Add candidates from Search or All CVs.")
    else:
        st.download_button(
            "Export shortlist CSV",
            cvs_to_dataframe(favorites).to_csv(index=False).encode("utf-8"),
            f"shortlist_{datetime.now():%Y%m%d}.csv",
            "text/csv",
            use_container_width=True,
        )
        for idx, candidate in enumerate(favorites, 1):
            render_candidate(candidate, idx, allow_favorite=False)
            if st.button("Remove from shortlist", key=f"remove_fav_{idx}_{candidate_key(candidate)}"):
                favorites.remove(candidate)
                st.session_state.favorite_keys.discard(candidate_key(candidate))
                st.rerun()

with help_tab:
    st.markdown('<div class="section-title">Help</div>', unsafe_allow_html=True)
    st.markdown(
        """
        **Recommended workflow**

        1. Sign in with Google or email.
        2. Select the target industry in the sidebar.
        3. Upload PDF, DOCX, or TXT CV files.
        4. Paste a detailed job description in Search.
        5. Adjust scoring weights if one hiring signal matters more than another.
        6. Add strong matches to the shortlist and export CSV.

        **Important notes**

        Google login now uses a hash-to-query bridge because Supabase returns OAuth tokens in the URL hash and Streamlit cannot read hashes on the server. The bridge converts the token into query parameters, completes the Supabase session, clears the URL, and opens the dashboard.

        Every ChromaDB record is scoped to the logged-in Supabase user id. This prevents the previous `default` session behavior from mixing users' uploaded CVs.
        """
    )

st.caption("TalentHire Pro | Private AI recruitment workspace")
