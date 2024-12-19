import asyncio
from uuid import uuid4

import pyperclip
import streamlit as st
from streamlit_chat import message

from core.ai_core.rag.entities.models import ParsedRAGResponse
from ui.authentication import (
    knowledge_warehouses_key,
    selected_knowledge_warehouse_key,
    chat_answers_history_key,
    user_prompt_history_key,
    chat_history_key,
    feedback_given_key,
    feedback_counts_key,
)


def render_style():
    st.markdown(
        """
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def on_knowledge_warehouse_change():
    # Clear chat history when switching knowledge warehouse
    st.session_state[chat_answers_history_key()] = []
    st.session_state[user_prompt_history_key()] = []
    st.session_state[chat_history_key()] = []
    st.session_state[feedback_given_key()] = {}

    # clear chat history in selected knowledge warehouse
    # TODO
    # sync the chat history of streamlit and ai_core
    # st.session_state[selected_knowledge_warehouse_key()].default_chat = []

    # Update selected knowledge warehouse
    kw_options = {
        kw.name: kw for kw in st.session_state[knowledge_warehouses_key()].values()
    }
    selected_kw_name = st.session_state.kw_selector
    kw = kw_options[selected_kw_name]
    st.session_state[selected_knowledge_warehouse_key()] = kw


def ask(kw, question) -> ParsedRAGResponse:
    # try:
    #     loop = asyncio.get_running_loop()
    # except RuntimeError:
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)

    try:
        response = asyncio.run(kw.aask_streaming(question))
        return response
    except Exception as e:
        import traceback

        st.error(f"Error generating response: {str(e)}\n\n{traceback.format_exc()}")
        return ParsedRAGResponse(answer="Error generating response")


# Add these helper functions
def regenerate_response(kw, prompt_index):
    if prompt_index < len(st.session_state[user_prompt_history_key()]):
        regenerate_prompt = st.session_state[user_prompt_history_key()][prompt_index]
        with st.spinner("Regenerating response..."):
            response = ask(kw, regenerate_prompt)
            st.session_state[chat_answers_history_key()][prompt_index] = response.answer
            st.session_state[feedback_given_key()][prompt_index] = None
            st.session_state.needs_rerun = True


def copy_to_clipboard(text):
    pyperclip.copy(text)


def update_feedback(index, type_):
    st.session_state[feedback_given_key()][index] = type_
    st.session_state[feedback_counts_key()][type_] += 1


def render_knowledge_warehouse_chat():
    render_style()

    if len(st.session_state[knowledge_warehouses_key()]) == 0:
        page = "Knowledge Warehouse Admin"
        st.rerun()

    st.header("Aeon Intelligence📚🔗 知識倉庫")

    # Fixed input container at bottom
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        prompt = st.text_input("質問", placeholder="Enter your message here...")
    with col2:
        # Add dropdown for knowledge warehouse selection
        kw_options = {
            kw.name: kw for kw in st.session_state[knowledge_warehouses_key()].values()
        }
        # Use the stored value as index if it exists
        index = (
            list(kw_options.keys()).index(
                st.session_state[selected_knowledge_warehouse_key()].name
            )
            if st.session_state[selected_knowledge_warehouse_key()]
            and st.session_state[selected_knowledge_warehouse_key()].name in kw_options
            else 0
        )
        selected_kw_name = st.selectbox(
            "知識倉庫",
            options=list(kw_options.keys()),
            key="kw_selector",
            index=index,
            on_change=on_knowledge_warehouse_change,
        )

        # Update selected knowledge warehouse
        kw = kw_options[selected_kw_name]
        st.session_state[selected_knowledge_warehouse_key()] = kw
    with col3:
        # Add vertical centering for submit button
        if st.button("Submit", key="submit"):
            prompt = prompt or "Hello"
            if prompt:
                with st.spinner("Generating response..."):
                    generated_response = ask(kw, prompt)
                    st.session_state[user_prompt_history_key()].append(prompt)
                    st.session_state[chat_answers_history_key()].append(
                        generated_response.answer
                    )
                    st.session_state[chat_history_key()].append(("human", prompt))
                    st.session_state[chat_history_key()].append(
                        ("ai", generated_response.answer)
                    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Chat messages container
    with st.container():
        if st.session_state[chat_answers_history_key()]:
            for idx, (generated_response, user_query) in enumerate(
                zip(
                    st.session_state[chat_answers_history_key()],
                    st.session_state[user_prompt_history_key()],
                )
            ):
                message(user_query, is_user=True, key=f"user_{uuid4()}")
                message(generated_response, key=f"bot_{idx}")

                # Get feedback status for this message
                feedback = st.session_state[feedback_given_key()].get(idx)

                # Buttons in horizontal row
                cols = st.columns([0.82, 0.045, 0.045, 0.045, 0.045])
                with cols[1]:
                    st.button(
                        "🔄",
                        key=f"regen_{idx}",
                        help="Regenerate",
                        on_click=lambda: regenerate_response(kw, idx),
                    )
                with cols[2]:
                    st.button(
                        "📋",
                        key=f"copy_{idx}",
                        help="Copy",
                        on_click=lambda: copy_to_clipboard(generated_response),
                    )
                with cols[3]:
                    st.button(
                        "👍",
                        key=f"good_{idx}",
                        help="Good",
                        disabled=feedback is not None,  # Disable if any feedback given
                        type="primary" if feedback == "good" else "secondary",
                        on_click=lambda index=idx: update_feedback(index, "good"),
                    )
                with cols[4]:
                    st.button(
                        "👎",
                        key=f"bad_{idx}",
                        help="Bad",
                        disabled=feedback is not None,  # Disable if any feedback given
                        type="primary" if feedback == "bad" else "secondary",
                        on_click=lambda index=idx: update_feedback(index, "bad"),
                    )
