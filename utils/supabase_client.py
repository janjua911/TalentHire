import os
import streamlit as st
from supabase import create_client, Client
from typing import Dict, Optional, List
import json

# Supabase credentials from secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase() -> Client:
    """Initialize Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_current_user_id() -> Optional[str]:
    """Get current logged-in user ID from session"""
    if 'user_id' in st.session_state:
        return st.session_state.user_id
    return None

def sign_up(email: str, password: str, company_name: str) -> Dict:
    """Register new company/user"""
    supabase = init_supabase()
    
    try:
        # Create auth user
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "company_name": company_name
                }
            }
        })
        
        # Create profile
        if response.user:
            supabase.table("profiles").insert({
                "id": response.user.id,
                "company_name": company_name,
                "company_email": email
            }).execute()
            
        return {"success": True, "user": response.user}
    except Exception as e:
        return {"success": False, "error": str(e)}

def sign_in(email: str, password: str) -> Dict:
    """Login existing company"""
    supabase = init_supabase()
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            st.session_state.user_id = response.user.id
            st.session_state.user_email = response.user.email
            
            # Get company profile
            profile = supabase.table("profiles")\
                .select("company_name")\
                .eq("id", response.user.id)\
                .execute()
            
            if profile.data:
                st.session_state.company_name = profile.data[0]["company_name"]
            
        return {"success": True, "user": response.user}
    except Exception as e:
        return {"success": False, "error": str(e)}

def sign_out():
    """Logout current user"""
    supabase = init_supabase()
    supabase.auth.sign_out()
    
    # Clear session
    for key in ['user_id', 'user_email', 'company_name']:
        if key in st.session_state:
            del st.session_state[key]

def save_cv_to_supabase(cv_data: Dict, embedding: List[float]) -> bool:
    """Save CV to Supabase with user isolation"""
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
            "embedding": embedding
        }).execute()
        return True
    except Exception as e:
        print(f"Error saving CV: {e}")
        return False

def get_user_cvs(field: Optional[str] = None) -> List[Dict]:
    """Get all CVs for current user only"""
    supabase = init_supabase()
    user_id = get_current_user_id()
    
    if not user_id:
        return []
    
    try:
        query = supabase.table("cvs")\
            .select("*")\
            .eq("user_id", user_id)
        
        if field:
            query = query.eq("field", field)
        
        response = query.execute()
        return response.data
    except Exception as e:
        print(f"Error getting CVs: {e}")
        return []
