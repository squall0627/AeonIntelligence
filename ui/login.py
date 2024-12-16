import streamlit as st
from ui.authentication import login


def render_style():
    st.markdown(
        """
        <style>
            /* Style for login form */
            [data-testid="stForm"] {
                max-width: 500px;
                margin: 0 auto;
                padding: 2rem;
                background-color: #1e1e1e;
                border-radius: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login_page():
    render_style()

    st.title("Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")  # Not used for now
        submit = st.form_submit_button("Login")

        if submit:
            if login(email):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Please enter a valid email address")
