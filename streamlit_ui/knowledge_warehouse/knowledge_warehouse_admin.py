import streamlit as st
import os
import sys
import tempfile
import asyncio
import nest_asyncio

from typing import List

from streamlit_ui.authentication import knowledge_warehouses_key, selected_knowledge_warehouse_key

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.ai_core.knowledge_warehouse.knowledge_warehouse import KnowledgeWarehouse
from core.ai_core.storage.storage_builder import StorageBuilder, StorageType
from core.ai_core.files.file import AIFile

from dotenv import load_dotenv

load_dotenv()

### import nest_asyncio ###
# nest_asyncio.apply()


def render_style():
    st.markdown(
        """
        <style>
            /* Style download buttons to look like links */
            .stDownloadButton > button {
                background: none!important;
                border: none;
                padding: 0!important;
                color: #4a90e2;
                text-decoration: underline;
                cursor: pointer;
                text-align: left;
            }
            .stDownloadButton > button:hover {
                color: #357abd;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def upload_to_temp_dir(files) -> List[str]:
    file_paths = []
    temp_dir = tempfile.mkdtemp()  # Create a temporary directory

    for file in files:
        # Use original filename in the temp directory
        temp_path = os.path.join(temp_dir, file.name)
        with open(temp_path, "wb") as f:
            f.write(file.getbuffer())
        file_paths.append(temp_path)

    return file_paths


def delete_temp_files(file_paths: List[str]):
    if file_paths:
        # Get the temp directory from the first file path
        temp_dir = os.path.dirname(file_paths[0])
        # Delete all files
        for path in file_paths:
            os.unlink(path)
        # Remove the temporary directory
        os.rmdir(temp_dir)


def save_knowledge_warehouse(kw: KnowledgeWarehouse):
    # try:
    #     loop = asyncio.get_running_loop()
    # except RuntimeError:
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)

    try:
        asyncio.run(
            kw.save(
                os.path.join(
                    os.getenv("LOCAL_KNOWLEDGE_WAREHOUSE_PATH"),
                    st.session_state.login_user_id,
                )
            )
        )
    except Exception as e:
        st.error(f"Error saving knowledge warehouse: {str(e)}")


def create_knowledge_warehouse(name: str, files, storage_path: str):
    try:
        # Save uploaded files temporarily
        file_paths = upload_to_temp_dir(files)

        # try:
        #     loop = asyncio.get_running_loop()
        # except RuntimeError:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)

        try:
            # Create knowledge warehouse
            kw = asyncio.run(
                KnowledgeWarehouse.afrom_files(
                    name=name,
                    file_paths=file_paths,
                    storage=StorageBuilder.build_storage(
                        StorageType.LocalStorage, storage_path, True
                    ),
                )
            )
        except Exception as e:
            st.error(f"Error creating knowledge warehouse: {str(e)}")
            return False
        finally:
            # Clean up temp files
            delete_temp_files(file_paths)

        # Save knowledge warehouse
        save_knowledge_warehouse(kw)

        st.session_state[knowledge_warehouses_key()][kw.kw_id] = kw
        st.session_state[selected_knowledge_warehouse_key()] = kw

        return True
    except Exception as e:
        st.error(f"Error creating knowledge warehouse: {str(e)}")
        return False


def get_knowledge_warehouse_files(kw: KnowledgeWarehouse):
    # try:
    #     loop = asyncio.get_running_loop()
    # except RuntimeError:
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    return asyncio.run(kw.storage.get_files())


def delete_file(kw: KnowledgeWarehouse, file: AIFile):
    # try:
    #     loop = asyncio.get_running_loop()
    # except RuntimeError:
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    asyncio.run(kw.delete_file(file))
    # save knowledge warehouse
    save_knowledge_warehouse(kw)


def add_files_to_knowledge_warehouse(kw: KnowledgeWarehouse, files) -> bool:
    try:
        # Save uploaded files temporarily
        file_paths = upload_to_temp_dir(files)

        # try:
        #     loop = asyncio.get_running_loop()
        # except RuntimeError:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)

        try:
            # Add files to existing knowledge warehouse
            asyncio.run(kw.aadd_files(file_paths))
        except Exception as e:
            st.error(f"Error adding files: {str(e)}")
            return False
        finally:
            # Clean up temp files
            delete_temp_files(file_paths)

        # Save knowledge warehouse
        save_knowledge_warehouse(kw)
        return True
    except Exception as e:
        st.error(f"Error adding files: {str(e)}")
        return False


async def delete_knowledge_warehouse(kw: KnowledgeWarehouse) -> bool:
    try:
        # try:
        #     loop = asyncio.get_running_loop()
        # except RuntimeError:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)

        # Delete the knowledge warehouse
        asyncio.run(kw.delete())

        # Remove from session state
        if knowledge_warehouses_key() in st.session_state:
            del st.session_state[knowledge_warehouses_key()][kw.kw_id]
        if st.session_state[selected_knowledge_warehouse_key()].kw_id == kw.kw_id:
            st.session_state[selected_knowledge_warehouse_key()] = None

        return True
    except Exception as e:
        st.error(f"Error deleting knowledge warehouse: {str(e)}")
        return False


def render_knowledge_warehouse_admin():
    render_style()

    st.title("Knowledge Warehouse Administration")

    # Create new knowledge warehouse section
    st.header("Create New Knowledge Warehouse")
    with st.form("new_kw_form"):
        kw_name = st.text_input("Knowledge Warehouse Name")
        # storage_path = st.text_input("Storage Path", value="./knowledge_warehouse_storage")
        storage_path = os.path.join(
            os.getenv("LOCAL_KNOWLEDGE_WAREHOUSE_STORAGE_PATH"),
            st.session_state.login_user_id,
        )
        uploaded_files = st.file_uploader(
            "Upload Knowledge Files",
            accept_multiple_files=True,
            type=["txt", "pdf", "doc", "docx", "csv"],
        )

        submit = st.form_submit_button("Create Knowledge Warehouse")

        if submit and kw_name and uploaded_files:
            os.makedirs(storage_path, exist_ok=True)
            if create_knowledge_warehouse(kw_name, uploaded_files, storage_path):
                st.success(f"Successfully created knowledge warehouse: {kw_name}")

    # Display existing knowledge warehouses
    st.header("Existing Knowledge Warehouses")

    if knowledge_warehouses_key() in st.session_state:
        for kw in st.session_state[knowledge_warehouses_key()].values():
            with st.expander(f"📚 {kw.name}"):
                # Add file upload section
                uploaded_files = st.file_uploader(
                    "Add Files",
                    accept_multiple_files=True,
                    type=["txt", "pdf", "doc", "docx", "csv"],
                    key=f"upload_{kw.kw_id}",
                )

                if uploaded_files:
                    if st.button("Add Files", key=f"add_files_{kw.kw_id}"):
                        if add_files_to_knowledge_warehouse(kw, uploaded_files):
                            st.success("Files added successfully!")
                            st.rerun()

                # Display existing files
                st.subheader("Files:")
                if kw.storage.nb_files() > 0:
                    files = get_knowledge_warehouse_files(kw)
                    for file in files:
                        col1, col2 = st.columns([0.5, 1])
                        with col1:
                            # File download button
                            with open(file.path, "rb") as f:
                                file_bytes = f.read()
                            st.download_button(
                                label=f"📄 {file.original_filename}",
                                data=file_bytes,
                                file_name=file.original_filename,
                                mime="application/octet-stream",
                                key=f"download_{file.file_id}",
                            )
                        with col2:
                            # Delete file button
                            if st.button("🗑️", key=f"delete_file_{file.file_id}"):
                                delete_file(kw, file)
                                st.rerun()
                else:
                    st.write("No files in this knowledge warehouse")

                # Add delete button with confirmation
                if st.button(
                    "Delete Knowledge Warehouse",
                    key=f"delete_{kw.kw_id}",
                    type="secondary",
                ):
                    st.session_state[f"confirm_delete_{kw.kw_id}"] = True

                # Show confirmation dialog
                if st.session_state.get(f"confirm_delete_{kw.kw_id}", False):
                    st.warning(
                        f"Are you sure you want to delete '{kw.name}'? This action cannot be undone."
                    )
                    col1, col2 = st.columns([0.2, 1])
                    with col1:
                        if st.button(
                            "Yes, delete it",
                            key=f"confirm_yes_{kw.kw_id}",
                            type="primary",
                        ):
                            if asyncio.run(delete_knowledge_warehouse(kw)):
                                st.success("Knowledge warehouse deleted successfully!")
                                st.rerun()
                    with col2:
                        if st.button("No, keep it", key=f"confirm_no_{kw.kw_id}"):
                            st.session_state[f"confirm_delete_{kw.kw_id}"] = False
                            st.rerun()
    else:
        st.write("No knowledge warehouses found")
