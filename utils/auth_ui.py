import streamlit as st
from utils.supabase_client import sign_up, sign_in, sign_out, get_current_user_id

def show_login_ui():
    """Display login/signup interface"""
    
    # If already logged in, show user info
    if get_current_user_id():
        st.sidebar.success(f"✅ Logged in as: {st.session_state.get('company_name', 'Company')}")
        
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            sign_out()
            st.rerun()
        return True
    
    # Show login/signup tabs
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        st.markdown("### Welcome Back!")
        
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", use_container_width=True):
            if email and password:
                result = sign_in(email, password)
                if result["success"]:
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(f"Login failed: {result.get('error', 'Unknown error')}")
            else:
                st.warning("Please enter email and password")
    
    with tab2:
        st.markdown("### Create New Account")
        st.info("🏢 Each company needs a separate account")
        
        company_name = st.text_input("Company Name", key="signup_company")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
        
        if st.button("Sign Up", use_container_width=True):
            if not all([company_name, email, password]):
                st.warning("Please fill all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                result = sign_up(email, password, company_name)
                if result["success"]:
                    st.success("Account created! Please login.")
                else:
                    st.error(f"Signup failed: {result.get('error', 'Unknown error')}")
    
    return False
