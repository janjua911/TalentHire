from __future__ import annotations

from typing import Dict, Optional, List, Any
import json

import streamlit as st
from supabase import create_client, Client


def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


SUPABASE_URL = _secret("SUPABASE_URL")
SUPABASE_KEY = _secret("SUPABASE_KEY")
DEFAULT_REDIRECT_URL = _secret("REDIRECT_URL", "http://localhost:8501")


@st.cache_resource(show_spinner=False)
def init_supabase() -> Client:
    """Initialize and cache the Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials are missing in .streamlit/secrets.toml")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _get_user_obj(response: Any) -> Any:
    return getattr(response, "user", None) or getattr(getattr(response, "session", None), "user", None)


def get_current_user_id() -> Optional[str]:
    return st.session_state.get("user_id")


def get_current_user_email() -> Optional[str]:
    return st.session_state.get("user_email")


def get_current_company_name() -> str:
    return st.session_state.get("company_name") or "Workspace"


def ensure_profile(user_id: str, email: str, company_name: Optional[str] = None) -> str:
    """Create or load a profile row for the authenticated user."""
    supabase = init_supabase()
    fallback_company = (company_name or (email.split("@")[0] if email else "Workspace")).strip() or "Workspace"

    try:
        profile = supabase.table("profiles").select("company_name, company_email").eq("id", user_id).execute()
        if profile.data:
            current_name = profile.data[0].get("company_name") or fallback_company
            st.session_state.company_name = current_name
            return current_name

        supabase.table("profiles").insert({
            "id": user_id,
            "company_name": fallback_company,
            "company_email": email,
        }).execute()
        st.session_state.company_name = fallback_company
        return fallback_company
    except Exception:
        st.session_state.company_name = fallback_company
        return fallback_company


def persist_auth_session(user_id: str, email: str, company_name: Optional[str] = None) -> None:
    st.session_state.user_id = user_id
    st.session_state.user_email = email
    st.session_state.company_name = ensure_profile(user_id, email, company_name)


def hydrate_session_from_supabase() -> bool:
    """Best-effort refresh of Streamlit session state from the Supabase client."""
    if get_current_user_id():
        return True

    try:
        supabase = init_supabase()
        response = supabase.auth.get_user()
        user = getattr(response, "user", None)
        if user:
            persist_auth_session(user.id, user.email or "")
            return True
    except Exception:
        return False
    return False


def sign_up(email: str, password: str, company_name: str) -> Dict:
    supabase = init_supabase()
    email = email.strip().lower()
    company_name = company_name.strip() or email.split("@")[0]

    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"company_name": company_name}},
        })
        user = _get_user_obj(response)
        if user:
            ensure_profile(user.id, email, company_name)
        return {"success": True, "user": user, "message": "Account created. Check your email if confirmation is enabled."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sign_in(email: str, password: str) -> Dict:
    supabase = init_supabase()
    email = email.strip().lower()

    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = _get_user_obj(response)
        if user:
            company_name = None
            try:
                company_name = (getattr(user, "user_metadata", None) or {}).get("company_name")
            except Exception:
                company_name = None
            persist_auth_session(user.id, user.email or email, company_name)
            return {"success": True, "user": user}
        return {"success": False, "error": "No user returned by Supabase."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# def sign_in_with_google(redirect_url: Optional[str] = None) -> Dict:
#     supabase = init_supabase()
#     try:
#         response = supabase.auth.sign_in_with_oauth({
#             "provider": "google",
#             "options": {
#                 "redirect_to": redirect_url or DEFAULT_REDIRECT_URL,
#                 "query_params": {"access_type": "offline", "prompt": "consent"},
#             },
#         })
#         return {"success": True, "url": response.url}
#     except Exception as e:
#         return {"success": False, "error": str(e)}


def complete_oauth_from_tokens(access_token: str, refresh_token: str = "") -> Dict:
    supabase = init_supabase()
    try:
        session = supabase.auth.set_session(access_token, refresh_token or "")
        user = _get_user_obj(session)
        if not user:
            response = supabase.auth.get_user(access_token)
            user = getattr(response, "user", None)
        if not user:
            return {"success": False, "error": "Google authentication succeeded but no Supabase user was returned."}
        persist_auth_session(user.id, user.email or "")
        return {"success": True, "user": user}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sign_out() -> None:
    try:
        init_supabase().auth.sign_out()
    except Exception:
        pass
    for key in ["user_id", "user_email", "company_name", "engine", "engine_user_id", "processed_cvs", "search_results", "favorites"]:
        st.session_state.pop(key, None)


def save_cv_to_supabase(cv_data: Dict, embedding: List[float]) -> bool:
    supabase = init_supabase()
    user_id = get_current_user_id()
    if not user_id:
        return False

    try:
        supabase.table("cvs").insert({
            "user_id": user_id,
            "filename": cv_data.get("filename"),
            "name": cv_data.get("name"),
            "email": cv_data.get("email"),
            "phone": cv_data.get("phone"),
            "location": cv_data.get("location"),
            "linkedin": cv_data.get("linkedin"),
            "github": cv_data.get("github"),
            "skills": json.dumps(cv_data.get("skills", [])),
            "certifications": json.dumps(cv_data.get("certifications", [])),
            "education": cv_data.get("education"),
            "experience": cv_data.get("experience"),
            "projects": cv_data.get("projects"),
            "years_of_experience": cv_data.get("years_of_experience", 0),
            "experience_level": cv_data.get("experience_level"),
            "education_level": cv_data.get("education_level"),
            "field": cv_data.get("field"),
            "embedding": embedding,
        }).execute()
        return True
    except Exception as e:
        print(f"Error saving CV: {e}")
        return False


def get_user_cvs(field: Optional[str] = None) -> List[Dict]:
    supabase = init_supabase()
    user_id = get_current_user_id()
    if not user_id:
        return []

    try:
        query = supabase.table("cvs").select("*").eq("user_id", user_id)
        if field:
            query = query.eq("field", field)
        return query.execute().data or []
    except Exception as e:
        print(f"Error getting CVs: {e}")
        return []
