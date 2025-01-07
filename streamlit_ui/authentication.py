# Add this helper function at the top level
import streamlit as st
import re
import requests


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


def login(username, password):
    st.title("Login")

    if st.button("Login"):
        response = requests.post(
            "http://localhost:8000/login_for_access_token",
            data={"username": username, "password": password},
        )

        if response.status_code == 200:
            token = response.json()["access_token"]
            st.session_state["token"] = token
            st.session_state["authenticated"] = True
            st.session_state.login_user_id = username
            return True
        else:
            return False


def logout():
    if st.button("Logout"):
        st.session_state["token"] = None
        st.session_state["authenticated"] = False
        st.rerun()


def check_authentication():
    return "authenticated" in st.session_state and st.session_state["authenticated"]


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
