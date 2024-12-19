import streamlit as st

from ui.footer import render_footer
from ui.sidebar import render_sidebar

st.set_page_config(
    page_title="Aeon Intelligence",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import nest_asyncio

from dotenv import load_dotenv
import sys
import os

from ui.authentication import (
    initialize_auth_state,
    knowledge_warehouses_key,
)
from ui.authentication import get_user_specific_key
from ui.knowledge_warehouse.knowledge_warehouse_admin import (
    render_knowledge_warehouse_admin,
)
from ui.knowledge_warehouse.knowledge_warehouse_chat import (
    render_knowledge_warehouse_chat,
)
from ui.login import render_login_page

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.ai_core.knowledge_warehouse import KnowledgeWarehouse

load_dotenv()


### import nest_asyncio ###
# nest_asyncio.apply()


def render_style():
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_knowledge_warehouses_paths(user_id: str):
    base_path = os.path.join(os.getenv("LOCAL_KNOWLEDGE_WAREHOUSE_PATH"), user_id)
    kw_paths = []

    # Check if path exists
    if os.path.exists(base_path):
        # Get only immediate subdirectories
        for item in os.listdir(base_path):
            full_path = os.path.join(base_path, item)
            if os.path.isdir(full_path):  # Check if it's a directory
                kw_paths.append(full_path)

    return kw_paths


# Modify the session state initialization
def initialize_session_state(user_id: str):
    # Chat history
    chat_answers_history_key = get_user_specific_key("chat_answers_history", user_id)
    if chat_answers_history_key not in st.session_state:
        st.session_state[chat_answers_history_key] = []

    user_prompt_history_key = get_user_specific_key("user_prompt_history", user_id)
    if user_prompt_history_key not in st.session_state:
        st.session_state[user_prompt_history_key] = []

    chat_history_key = get_user_specific_key("chat_history", user_id)
    if chat_history_key not in st.session_state:
        st.session_state[chat_history_key] = []

    # Feedback
    feedback_counts_key = get_user_specific_key("feedback_counts", user_id)
    if feedback_counts_key not in st.session_state:
        st.session_state[feedback_counts_key] = {"good": 0, "bad": 0}

    feedback_given_key = get_user_specific_key("feedback_given", user_id)
    if feedback_given_key not in st.session_state:
        st.session_state[feedback_given_key] = {}

    # initialize knowledge warehouse
    knowledge_warehouses_key = get_user_specific_key("knowledge_warehouses", user_id)
    if knowledge_warehouses_key not in st.session_state:
        st.session_state[knowledge_warehouses_key] = {}
        # Load all knowledge warehouses of login user
        for kw_path in get_knowledge_warehouses_paths(user_id):
            kw = KnowledgeWarehouse.load(kw_path)
            st.session_state[knowledge_warehouses_key][kw.kw_id] = kw

    # initialize selected knowledge warehouse
    selected_knowledge_warehouse_key = get_user_specific_key(
        "selected_knowledge_warehouse", user_id
    )
    if selected_knowledge_warehouse_key not in st.session_state:
        st.session_state[selected_knowledge_warehouse_key] = None


def main():
    render_style()

    initialize_auth_state()

    if not st.session_state.authenticated:
        render_login_page()
        return

    user_id = st.session_state.login_user_id

    if "needs_rerun" in st.session_state and st.session_state.needs_rerun:
        st.session_state.needs_rerun = False
        st.rerun()

    initialize_session_state(user_id)

    # Sidebar user information
    page = render_sidebar()

    # When the login user does not have any knowledge warehouse, show the knowledge warehouse admin page
    if len(st.session_state[knowledge_warehouses_key()]) == 0:
        page = "Knowledge Warehouse Admin"

    if page == "Knowledge Warehouse Chat":
        render_knowledge_warehouse_chat()

    elif page == "Knowledge Warehouse Admin":
        render_knowledge_warehouse_admin()

    render_footer()


if __name__ == "__main__":
    main()
