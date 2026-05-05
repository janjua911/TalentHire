# TalentHire Pro - Fixed Build

## What was fixed

- Google OAuth redirect now lands on the dashboard instead of returning to the email/password login page.
- Added a JavaScript hash-to-query bridge for Supabase OAuth tokens because Streamlit cannot read URL hash fragments on the Python server.
- Fixed missing `sign_out` import/runtime crash.
- Fixed user isolation by initializing ChromaDB/RAG with the logged-in Supabase user id instead of the old `default` session id.
- Rebuilt the login UI with a clean black/white TalentHire Pro logo and no emoji-based branding.
- Rebuilt the main UI with cleaner cards, metrics, tabs, shortlist workflow, export buttons, and better empty/error states.
- Improved email/password form validation and password checks.
- Google OAuth now uses `REDIRECT_URL` from `.streamlit/secrets.toml` instead of hard-coded localhost.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Required Streamlit secrets

Create or update `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "your_supabase_project_url"
SUPABASE_KEY = "your_supabase_anon_or_publishable_key"
REDIRECT_URL = "http://localhost:8501"
```

For deployment, set `REDIRECT_URL` to your deployed Streamlit app URL and add the same URL in Supabase Authentication redirect URLs.
