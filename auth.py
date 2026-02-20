import streamlit as st
from datetime import datetime

# Simple users dictionary - no bcrypt needed
USERS = {
    "admin": {
        "id": 1,
        "username": "admin",
        "password": "admin123",  # Plain text for demo
        "full_name": "System Administrator",
        "role": "admin",
        "station_id": None,
        "shift_id": None,
        "is_active": True
    },
    "supervisor": {
        "id": 2,
        "username": "supervisor",
        "password": "super123",
        "full_name": "Shift Supervisor",
        "role": "supervisor",
        "station_id": None,
        "shift_id": 1,
        "is_active": True
    },
    "operator": {
        "id": 3,
        "username": "operator",
        "password": "op123",
        "full_name": "Assembly Operator",
        "role": "operator",
        "station_id": 3,
        "shift_id": 1,
        "is_active": True
    },
    "demo": {
        "id": 999,
        "username": "demo",
        "password": "demo123",
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
    """Check if user is logged in, if not show login form"""
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if st.session_state.user is None:
        st.title("🔐 AeroTwin H-125 - Production Access")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            col1, col2 = st.columns(2)
            
            with col1:
                submitted = st.form_submit_button("Login", use_container_width=True)
            
            with col2:
                if st.form_submit_button("Demo Access", use_container_width=True):
                    st.session_state.user = USERS["demo"]
                    st.rerun()
            
            if submitted:
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
        - Supervisor: `supervisor` / `super123`  
        - Operator: `operator` / `op123`  
        - Demo: `demo` / `demo123`
        """)
        
        return False
    return True

def logout():
    """Log out current user"""
    st.session_state.user = None
    st.rerun()

def get_current_user():
    """Get current logged in user"""
    return st.session_state.get('user', None)

def require_role(roles):
    """Check if user has required role"""
    user = get_current_user()
    if not user:
        st.error("⛔ Please login first")
        st.stop()
    if user['role'] not in roles:
        st.error(f"⛔ You need {roles} role to access this page")
        st.stop()
