from __future__ import annotations

import html
import re

import streamlit as st
import streamlit.components.v1 as components

from utils.supabase_client import (
    get_current_user_id,
    sign_in,
    sign_in_with_google,
    sign_up,
    DEFAULT_REDIRECT_URL,
)


def inject_oauth_hash_bridge() -> None:
    """Move Supabase OAuth tokens from URL hash to query params Streamlit can read."""
    components.html(
        """
        <script>
        (function () {
          const parentWindow = window.parent;
          const loc = parentWindow.location;
          if (!loc.hash || !loc.hash.includes('access_token=')) return;

          const hashParams = new URLSearchParams(loc.hash.substring(1));
          const url = new URL(loc.href);
          ['access_token', 'refresh_token', 'expires_in', 'token_type', 'provider_token'].forEach(function (key) {
            const value = hashParams.get(key);
            if (value) url.searchParams.set(key, value);
          });
          url.hash = '';
          parentWindow.location.replace(url.toString());
        })();
        </script>
        """,
        height=0,
    )


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


def _password_errors(password: str) -> list[str]:
    errors = []
    if len(password) < 8:
        errors.append("Use at least 8 characters.")
    if not re.search(r"[A-Za-z]", password):
        errors.append("Add at least one letter.")
    if not re.search(r"\d", password):
        errors.append("Add at least one number.")
    return errors


def _safe_error(message: str) -> str:
    cleaned = (message or "Authentication failed.").strip()
    return html.escape(cleaned[:220])


def show_login_ui() -> bool:
    if get_current_user_id():
        return False

    inject_oauth_hash_bridge()

    st.markdown(
        """
        <style>
          .auth-page {
            min-height: 82vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem 0;
          }
          .auth-shell {
            width: min(960px, 100%);
            display: grid;
            grid-template-columns: 1.05fr .95fr;
            gap: 1.25rem;
            align-items: stretch;
          }
          .brand-panel, .auth-panel {
            background: rgba(255,255,255,.045);
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 28px;
            box-shadow: 0 30px 80px rgba(0,0,0,.32);
          }
          .brand-panel { padding: 2.25rem; }
          .auth-panel { padding: 1.6rem; }
          .logo-mark {
            width: 64px;
            height: 64px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,.18);
            display: grid;
            place-items: center;
            font-weight: 900;
            color: #fff;
            letter-spacing: -0.08em;
            margin-bottom: 1.4rem;
            background: linear-gradient(145deg, #111 0%, #2f2f2f 50%, #fff 51%, #d7d7d7 100%);
          }
          .brand-title { font-size: 2.45rem; font-weight: 850; line-height: 1.05; letter-spacing: -.05em; color: #fff; margin: 0 0 .8rem; }
          .brand-copy { color: #a7adbb; font-size: 1rem; line-height: 1.65; max-width: 34rem; }
          .brand-points { margin-top: 1.4rem; display: grid; gap: .7rem; color: #d9dde7; }
          .brand-point { border: 1px solid rgba(255,255,255,.09); border-radius: 14px; padding: .72rem .9rem; background: rgba(255,255,255,.035); }
          .auth-title { color: #fff; margin: .2rem 0 .25rem; font-size: 1.55rem; font-weight: 800; letter-spacing: -.03em; }
          .auth-subtitle { color: #9ca3af; margin: 0 0 1rem; }
          .or-line { display:flex; align-items:center; gap:.75rem; color:#858b98; margin:1rem 0; font-size:.9rem; }
          .or-line:before, .or-line:after { content:""; height:1px; background:rgba(255,255,255,.12); flex:1; }
          @media (max-width: 820px) { .auth-shell { grid-template-columns: 1fr; } .brand-title { font-size: 2rem; } }
        </style>
        <div class="auth-page"><div class="auth-shell">
          <section class="brand-panel">
            <div class="logo-mark">TH</div>
            <h1 class="brand-title">TalentHire Pro</h1>
            <p class="brand-copy">A focused CV screening workspace for recruiters who need semantic search, weighted scoring, analytics, and clean candidate shortlisting.</p>
            <div class="brand-points">
              <div class="brand-point">Private workspace per authenticated user</div>
              <div class="brand-point">Google or email authentication with one clean landing flow</div>
              <div class="brand-point">Weighted scoring across skills, experience, education, projects, and certifications</div>
            </div>
          </section>
          <section class="auth-panel">
            <h2 class="auth-title">Sign in</h2>
            <p class="auth-subtitle">Use Google or email. Both routes now land directly in the dashboard.</p>
        """,
        unsafe_allow_html=True,
    )

    google_clicked = st.button("Continue with Google", use_container_width=True, type="primary")
    if google_clicked:
        result = sign_in_with_google(DEFAULT_REDIRECT_URL)
        if result.get("success") and result.get("url"):
            st.markdown(f'<meta http-equiv="refresh" content="0; url={html.escape(result["url"], quote=True)}">', unsafe_allow_html=True)
            st.link_button("Open Google sign-in", result["url"], use_container_width=True)
            st.stop()
        st.error(_safe_error(result.get("error", "Google login failed.")))

    st.markdown('<div class="or-line"><span>or continue with email</span></div>', unsafe_allow_html=True)

    sign_in_tab, sign_up_tab = st.tabs(["Email sign in", "Create account"])

    with sign_in_tab:
        with st.form("email_sign_in", clear_on_submit=False):
            email = st.text_input("Email", key="login_email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")

        if submitted:
            if not _valid_email(email):
                st.error("Enter a valid email address.")
            elif not password:
                st.error("Enter your password.")
            else:
                result = sign_in(email, password)
                if result.get("success"):
                    st.rerun()
                st.error(_safe_error(result.get("error", "Invalid email or password.")))

    with sign_up_tab:
        with st.form("email_sign_up", clear_on_submit=False):
            company = st.text_input("Company name", key="signup_company", placeholder="Acme Hiring")
            email = st.text_input("Work email", key="signup_email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
            submitted = st.form_submit_button("Create account", use_container_width=True)

        if submitted:
            password_issues = _password_errors(password)
            if not company.strip():
                st.error("Enter a company name.")
            elif not _valid_email(email):
                st.error("Enter a valid email address.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif password_issues:
                st.error(" ".join(password_issues))
            else:
                result = sign_up(email, password, company)
                if result.get("success"):
                    st.success(result.get("message", "Account created. You can sign in now."))
                else:
                    st.error(_safe_error(result.get("error", "Signup failed.")))

    st.markdown("</section></div></div>", unsafe_allow_html=True)
    st.stop()
    return True
