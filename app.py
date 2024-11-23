import streamlit as st

st.set_page_config(
    page_title="Aeon Intelligence",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import asyncio
import nest_asyncio
from uuid import uuid4

from dotenv import load_dotenv
import sys
import os

from frontend.authentication import initialize_auth_state
from frontend.authentication import get_user_specific_key
from frontend.knowledge_warehouse_admin import render_knowledge_warehouse_admin
from frontend.login import render_login_page

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.ai_core.rag.entities.models import ParsedRAGResponse
from core.ai_core.knowledge_warehouse import KnowledgeWarehouse

load_dotenv()


from streamlit_chat import message

import pyperclip  # Add this import for clipboard functionality

### import nest_asyncio ###
nest_asyncio.apply()

# Add these imports
from PIL import Image
import requests
from io import BytesIO


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
    selected_knowledge_warehouse_key = get_user_specific_key("selected_knowledge_warehouse", user_id)
    if selected_knowledge_warehouse_key not in st.session_state:
        st.session_state[selected_knowledge_warehouse_key] = None

# Add this function to get a profile picture
def get_profile_picture(email):
    # This uses Gravatar to get a profile picture based on email
    # You can replace this with a different service or use a default image
    gravatar_url = f"https://www.gravatar.com/avatar/{hash(email)}?d=identicon&s=200"
    response = requests.get(gravatar_url)
    img = Image.open(BytesIO(response.content))
    return img


# Custom CSS for dark theme and modern look
st.markdown(
    """
<style>
    .stApp {
        background-color: #1E1E1E;
        color: #FFFFFF;
    }
    .stTextInput > div > div > input {
        background-color: #2D2D2D;
        color: #FFFFFF;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: #FFFFFF;
    }
    .stSidebar {
        background-color: #252526;
    }
    .stMessage {
        background-color: #2D2D2D;
    }
    /* Updated chat container styles */
    .chat-container {
        display: flex;
        flex-direction: column;
        height: calc(100vh - 300px); /* Adjust for header and input container */
        overflow-y: auto;
        padding: 20px;
        background-color: #2D2D2D;
        border-radius: 10px;
        margin-bottom: 80px;  /* Space for input container */
    }
    /* Updated input container styles */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #1E1E1E;
        padding: 1rem;
        z-index: 100;
        border-top: 1px solid #333;
    }

    /* Ensure messages stack properly */
    .stChatMessage {
        margin-bottom: 1rem;
    }
    /* Message action buttons */
    .message-actions {
        display: flex;
        gap: 8px;
        margin-top: 8px;
    }
    
    .message-action-btn {
        padding: 4px 8px;
        border-radius: 4px;
        border: 1px solid #4CAF50;
        background: transparent;
        color: #4CAF50;
        cursor: pointer;
    }
    
    .message-action-btn:hover {
        background: #4CAF5022;
    }
    
    /* Reduce spacing between buttons */
    .stButton {
        margin-right: -10px;  /* Reduce right margin */
    }

    /* Button styling */
    .stButton > button {
        background-color: transparent;
        border: 1px solid #333;
        border-radius: 4px;
        color: #fff;
        padding: 4px 8px;
        font-size: 12px;
        transition: all 0.2s;
        min-width: 32px;  /* Set minimum width */
        height: 32px;     /* Set fixed height */
    }
    
    .stButton > button:hover {
        background-color: #333;
        border-color: #666;
    }

    /* Style for disabled buttons */
    .stButton > button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
    
    /* Style for selected feedback */
    .stButton > button[data-baseweb="button"][kind="primary"] {
        border-color: #4CAF50;
        color: #4CAF50;
    }
    
    /* Container spacing */
    .element-container {
        margin-bottom: 0.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("""
<style>
    /* Button styling */
    .stButton > button {
        background-color: transparent;
        border: 1px solid #333;
        border-radius: 4px;
        color: #fff;
        padding: 4px 8px;
        font-size: 12px;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #333;
        border-color: #666;
    }
    
    /* Container spacing */
    .element-container {
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Add to your custom CSS section
st.markdown("""
<style>
    /* Make dropdown more compact */
    .stSelectbox {
        max-width: auto;  /* Limit width */
    }
    
    /* Reduce padding in dropdown */
    .stSelectbox > div > div {
        padding: 2px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
    /* Align submit button vertically */
    .stButton {
        margin-top: 25px;  /* Adjust this value to fine-tune vertical alignment */
    }
    
    /* Make button same height as input */
    .stButton > button {
        height: 38px;  /* Match Streamlit's default input height */
        margin-top: 0;
        padding-top: 3px;
        padding-bottom: 3px;
    }
</style>
""", unsafe_allow_html=True)


def main():

    initialize_auth_state()
    
    if not st.session_state.authenticated:
        render_login_page()
        return
    
    user_id = st.session_state.login_user_id

    if "needs_rerun" in st.session_state and st.session_state.needs_rerun:
        st.session_state.needs_rerun = False
        st.rerun()

    initialize_session_state(user_id)

    # Update your existing code to use user-specific keys
    chat_answers_history_key = get_user_specific_key("chat_answers_history", user_id)
    user_prompt_history_key = get_user_specific_key("user_prompt_history", user_id)
    chat_history_key = get_user_specific_key("chat_history", user_id)
    feedback_given_key = get_user_specific_key("feedback_given", user_id)
    feedback_counts_key = get_user_specific_key("feedback_counts", user_id)
    knowledge_warehouses_key = get_user_specific_key("knowledge_warehouses", user_id)
    selected_knowledge_warehouse_key = get_user_specific_key("selected_knowledge_warehouse", user_id)

    def on_knowledge_warehouse_change():
        # Clear chat history when switching knowledge warehouse
        st.session_state[chat_answers_history_key] = []
        st.session_state[user_prompt_history_key] = []
        st.session_state[chat_history_key] = []
        st.session_state[feedback_given_key] = {}

        # clear chat history in selected knowledge warehouse
        st.session_state[selected_knowledge_warehouse_key].default_chat = []
        
        # Update selected knowledge warehouse
        kw_options = {kw.name: kw for kw in st.session_state[knowledge_warehouses_key].values()}
        selected_kw_name = st.session_state.kw_selector
        kw = kw_options[selected_kw_name]
        st.session_state[selected_knowledge_warehouse_key] = kw

    def ask(question) -> ParsedRAGResponse:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            response = loop.run_until_complete(kw.aask_streaming(question))
            return response
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return ParsedRAGResponse(answer="Error generating response")

    # Add these helper functions
    def regenerate_response(prompt_index):
        if prompt_index < len(st.session_state[user_prompt_history_key]):
            regenerate_prompt = st.session_state[user_prompt_history_key][prompt_index]
            with st.spinner("Regenerating response..."):
                response = ask(regenerate_prompt)
                st.session_state[chat_answers_history_key][prompt_index] = response.answer
                st.session_state[feedback_given_key][prompt_index] = None
                st.session_state.needs_rerun = True

    def copy_to_clipboard(text):
        pyperclip.copy(text)

    def update_feedback(index, type_):
        st.session_state[feedback_given_key][index] = type_
        st.session_state[feedback_counts_key][type_] += 1

    # Sidebar user information
    with st.sidebar:
        st.title("User Profile")

        # You can replace these with actual user data
        user_name = user_id.split("@")[0]
        user_email = user_id

        profile_pic = get_profile_picture(user_email)
        st.image(profile_pic, width=150)
        st.write(f"**Name:** {user_name}")
        st.write(f"**Email:** {user_email}")

    # Add feedback counter display in sidebar
    with st.sidebar:
        st.write("---")
        st.write("### Feedback Statistics")
        st.write(f"👍 Good responses: {st.session_state[feedback_counts_key]['good']}")
        st.write(f"👎 Bad responses: {st.session_state[feedback_counts_key]['bad']}")

    # Add this to your sidebar or main content
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page", 
        ["Chat", "Knowledge Warehouse"]
    )

    # When the login user does not have any knowledge warehouse, show the knowledge warehouse admin page
    if len(st.session_state[knowledge_warehouses_key]) == 0:
        page = "Knowledge Warehouse"

    if page == "Chat":
        if len(st.session_state[knowledge_warehouses_key]) == 0:
            page = "Knowledge Warehouse"
            st.rerun()

        st.header("Aeon Intelligence📚🔗 知識倉庫")

        # Fixed input container at bottom
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            prompt = st.text_input("質問", placeholder="Enter your message here...")
        with col2:
            # Add dropdown for knowledge warehouse selection
            kw_options = {kw.name: kw for kw in st.session_state[knowledge_warehouses_key].values()}
            # Use the stored value as index if it exists
            index = list(kw_options.keys()).index(st.session_state[selected_knowledge_warehouse_key].name) \
                if st.session_state[selected_knowledge_warehouse_key] and st.session_state[selected_knowledge_warehouse_key].name in kw_options else 0
            selected_kw_name = st.selectbox(
                "知識倉庫",
                options=list(kw_options.keys()),
                key="kw_selector",
                index=index,
                on_change=on_knowledge_warehouse_change
            )
            
            # Update selected knowledge warehouse
            kw = kw_options[selected_kw_name]
            st.session_state[selected_knowledge_warehouse_key] = kw
        with col3:
            # Add vertical centering for submit button
            if st.button("Submit", key="submit"):
                prompt = prompt or "Hello"
                if prompt:
                    with st.spinner("Generating response..."):
                        generated_response = ask(prompt)
                        st.session_state[user_prompt_history_key].append(prompt)
                        st.session_state[chat_answers_history_key].append(generated_response.answer)
                        st.session_state[chat_history_key].append(("human", prompt))
                        st.session_state[chat_history_key].append(("ai", generated_response.answer))
        st.markdown('</div>', unsafe_allow_html=True)

        # Chat messages container
        with st.container():
            if st.session_state[chat_answers_history_key]:
                for idx, (generated_response, user_query) in enumerate(zip(
                        st.session_state[chat_answers_history_key],
                        st.session_state[user_prompt_history_key],
                )):
                    message(user_query, is_user=True, key=f"user_{uuid4()}")
                    message(generated_response, key=f"bot_{idx}")
                    
                    # Get feedback status for this message
                    feedback = st.session_state[feedback_given_key].get(idx)

                    # Buttons in horizontal row
                    cols = st.columns([0.82, 0.045, 0.045, 0.045, 0.045])
                    with cols[1]:
                        st.button("🔄", key=f"regen_{idx}", help="Regenerate", on_click=lambda: regenerate_response(idx))
                    with cols[2]:
                        st.button("📋", key=f"copy_{idx}", help="Copy", on_click=lambda: copy_to_clipboard(generated_response))
                    with cols[3]:
                        st.button("👍", 
                                    key=f"good_{idx}", 
                                    help="Good",
                                    disabled=feedback is not None,  # Disable if any feedback given
                                    type="primary" if feedback == "good" else "secondary",
                                    on_click=lambda index=idx: update_feedback(index, "good"))
                    with cols[4]:
                        st.button("👎", 
                                    key=f"bad_{idx}", 
                                    help="Bad",
                                    disabled=feedback is not None,  # Disable if any feedback given
                                    type="primary" if feedback == "bad" else "secondary",
                                    on_click=lambda index=idx: update_feedback(index, "bad"))
                        
        # Add a footer
        st.markdown("---")
        st.markdown("Powered by LangChain and Streamlit")
        st.markdown("Copyright © 2024 AEON CO., LTD. All rights reserved.")

    elif page == "Knowledge Warehouse":
        render_knowledge_warehouse_admin()

if __name__ == "__main__":
    main()
