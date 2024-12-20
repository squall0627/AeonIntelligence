# Add this helper function at the top level
import streamlit as st
import re


def get_user_specific_key(base_key: str, user_id: str) -> str:
    return f"user_{user_id}_{base_key}"


def is_valid_email(email: str) -> bool:
    """Check if string is a valid email."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def initialize_auth_state():
    """Initialize authentication-related session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "login_user_id" not in st.session_state:
        st.session_state.login_user_id = None


def login(email: str) -> bool:
    """Handle user login."""
    if is_valid_email(email):
        st.session_state.authenticated = True
        st.session_state.login_user_id = email
        return True
    return False


def logout():
    """Handle user logout."""
    st.session_state.authenticated = False
    st.session_state.login_user_id = None
    # Clear other user-specific session state
    for key in list(st.session_state.keys()):
        if key.startswith(f"user_{st.session_state.login_user_id}_"):
            del st.session_state[key]


def chat_answers_history_key() -> str:
    user_id = st.session_state.login_user_id
    return get_user_specific_key("chat_answers_history", user_id)


def user_prompt_history_key() -> str:
    user_id = st.session_state.login_user_id
    return get_user_specific_key("user_prompt_history", user_id)


def chat_history_key() -> str:
    user_id = st.session_state.login_user_id
    return get_user_specific_key("chat_history", user_id)


def feedback_given_key() -> str:
    user_id = st.session_state.login_user_id
    return get_user_specific_key("feedback_given", user_id)


def feedback_counts_key() -> str:
    user_id = st.session_state.login_user_id
    return get_user_specific_key("feedback_counts", user_id)


def knowledge_warehouses_key() -> str:
    user_id = st.session_state.login_user_id
    return get_user_specific_key("knowledge_warehouses", user_id)


def selected_knowledge_warehouse_key() -> str:
    user_id = st.session_state.login_user_id
    return get_user_specific_key("selected_knowledge_warehouse", user_id)
