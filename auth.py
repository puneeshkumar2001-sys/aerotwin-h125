import streamlit as st
from datetime import datetime

# Simple users dictionary - no bcrypt needed
USERS = {
    "admin": {
        "id": 1,
        "username": "admin",
        "password": "admin123",  # Plain text
        "full_name": "System Administrator",
        "role": "admin",
        "station_id": None,
        "shift_id": None,
        "is_active": True
    },
    "demo": {
        "id": 999,
        "username": "demo",
        "password": "demo123",  # Plain text
        "full_name": "Demo User",
        "role": "viewer",
        "station_id": None,
        "shift_id": None,
        "is_active": True
    }
}

def authenticate_user(username, password):
    """Simple authentication - no bcrypt needed"""
    if username in USERS and USERS[username]["password"] == password:
        return USERS[username]
    return None

def login_required():
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if st.session_state.user is None:
        st.title("🔐 AeroTwin H-125 - Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login"):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        st.markdown("---")
        st.markdown("""
        **Demo Credentials:**  
        - Admin: `admin` / `admin123`  
        - Demo: `demo` / `demo123`
        """)
        
        return False
    return True

def logout():
    st.session_state.user = None
    st.rerun()

def get_current_user():
    return st.session_state.get('user', None)
