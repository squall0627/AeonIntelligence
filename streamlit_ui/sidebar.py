import streamlit as st
import requests

from PIL import Image
from io import BytesIO

from streamlit_ui.authentication import feedback_counts_key


def render_style():
    st.markdown(
        """
        <style>
            .stSidebar {
                background-color: #252526;
            }
            
            /* Style for user profile in sidebar */
            .user-profile {
                padding: 1rem;
                margin-top: 1rem;
                border-top: 1px solid #333;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Add this function to get a profile picture
def get_profile_picture(email):
    # This uses Gravatar to get a profile picture based on email
    # You can replace this with a different service or use a default image
    gravatar_url = f"https://www.gravatar.com/avatar/{hash(email)}?d=identicon&s=200"
    response = requests.get(gravatar_url)
    img = Image.open(BytesIO(response.content))
    return img


def render_navigation():
    nav_items = {
        "Home": "🏠",
        "Chat": "💬",
        "Knowledge Warehouse": "📚",
        "Brain Studio": "🧠",
        "Text Translation": "🌐",
        "File Translation": "📘",
    }

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Knowledge Warehouse"

    for page, icon in nav_items.items():
        if st.sidebar.button(f"{icon} {page}", key=page):
            st.session_state.current_page = page
            st.rerun()


def render_sidebar():
    render_style()

    user_id = st.session_state.login_user_id
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
        st.write(
            f"👍 Good responses: {st.session_state[feedback_counts_key()]['good']}"
        )
        st.write(f"👎 Bad responses: {st.session_state[feedback_counts_key()]['bad']}")

    # Add this to your sidebar or main content
    st.sidebar.title("Navigation")
    # page = st.sidebar.selectbox(
    #     "Choose a page", ["Knowledge Warehouse Chat", "Knowledge Warehouse Admin"]
    # )
    render_navigation()

    return st.session_state.current_page
