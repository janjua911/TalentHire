import streamlit as st
from utils.supabase_client import sign_in_with_google, init_supabase

st.set_page_config(page_title="Test Google Auth", layout="centered")

st.title("Google Sign-In Test")

# Check if already logged in
if 'user_id' in st.session_state:
    st.success(f"✅ Logged in as: {st.session_state.get('user_email')}")
    if st.button("Logout"):
        for key in ['user_id', 'user_email', 'company_name']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
else:
    # Check for OAuth redirect
    query_params = st.query_params
    if "access_token" in query_params:
        supabase = init_supabase()
        supabase.auth.set_session(query_params["access_token"], query_params.get("refresh_token", ""))
        user = supabase.auth.get_user()
        if user.user:
            st.session_state.user_id = user.user.id
            st.session_state.user_email = user.user.email
            st.query_params.clear()
            st.rerun()
    
    # Show login button
    st.markdown("### Sign in to continue")
    if st.button("🔐 Sign in with Google", use_container_width=True):
        result = sign_in_with_google()
        if result.get("url"):
            st.markdown(f'<meta http-equiv="refresh" content="0; url={result["url"]}">', unsafe_allow_html=True)
            st.info("Redirecting to Google...")
        else:
            st.error(f"Error: {result.get('error')}")