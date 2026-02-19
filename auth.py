import bcrypt
import streamlit as st
from datetime import datetime
from database import db
import sqlite3

def hash_password(password):
    """Hash a password for storing."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, hash):
    """Verify a stored password against one provided by user"""
    return bcrypt.checkpw(password.encode('utf-8'), hash.encode('utf-8'))

def authenticate_user(username, password):
    """Authenticate user credentials"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, password_hash, full_name, role, station_id, shift_id, is_active
            FROM users WHERE username = ? AND is_active = 1
        ''', (username,))
        
        user = cursor.fetchone()
        
        if user and verify_password(password, user['password_hash']):
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = ? WHERE id = ?
            ''', (datetime.now(), user['id']))
            conn.commit()
            
            return dict(user)
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
                if st.form_submit_button("Demo Access (Read Only)", use_container_width=True):
                    st.session_state.user = {
                        'id': 999,
                        'username': 'demo',
                        'full_name': 'Demo User',
                        'role': 'viewer',
                        'station_id': None,
                        'shift_id': None
                    }
                    st.rerun()
            
            if submitted:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    db.log_event('LOGIN', f'User {username} logged in', user_id=user['id'])
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        st.markdown("---")
        st.markdown("""
        **Demo Credentials:**  
        - Username: `demo` (click Demo Access button)  
        - Admin: `admin` / `admin123` (change on first login)
        """)
        
        return False
    return True

def logout():
    if 'user' in st.session_state:
        db.log_event('LOGOUT', f'User {st.session_state.user["username"]} logged out', 
                    user_id=st.session_state.user['id'])
    st.session_state.user = None
    st.rerun()

def get_current_user():
    return st.session_state.get('user', None)

def require_role(roles):
    """Decorator to check user role"""
    user = get_current_user()
    if not user or user['role'] not in roles:
        st.error("⛔ You don't have permission to access this page")
        st.stop()
