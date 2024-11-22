import streamlit as st
import os
import sys
import tempfile
import asyncio
import nest_asyncio

from typing import List

from frontend.authentication import get_user_specific_key

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.ai_core.knowledge_warehouse.knowledge_warehouse import KnowledgeWarehouse
from core.ai_core.storage.storage_builder import StorageBuilder, StorageType

from dotenv import load_dotenv
load_dotenv()

### import nest_asyncio ###
nest_asyncio.apply()

# TODO Assuming you have the user_id from login
user_id = "chin-hiro@aeonpeople.biz"  # Replace with actual user ID from your login system
st.session_state.login_user_id = user_id

knowledge_warehouses_key = get_user_specific_key("knowledge_warehouses", st.session_state.login_user_id)
selected_knowledge_warehouse_key = get_user_specific_key("selected_knowledge_warehouse", st.session_state.login_user_id)


def upload_to_temp_dir(files) -> List[str]:
    file_paths = []
    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.name) as tmp_file:
            tmp_file.write(file.getbuffer())
            file_paths.append(tmp_file.name)
    return file_paths

def delete_temp_files(file_paths: List[str]):
    for path in file_paths:
        os.unlink(path)

def save_knowledge_warehouse(kw: KnowledgeWarehouse):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(kw.save(os.path.join(os.getenv("LOCAL_KNOWLEDGE_WAREHOUSE_PATH"), st.session_state.login_user_id)))
    except Exception as e:
        st.error(f"Error saving knowledge warehouse: {str(e)}")

def create_knowledge_warehouse(name: str, files, storage_path: str):
    try:
        # Save uploaded files temporarily
        file_paths = upload_to_temp_dir(files)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            # Create knowledge warehouse
            kw = loop.run_until_complete(KnowledgeWarehouse.afrom_files(
            name=name,
            file_paths=file_paths,
            storage=StorageBuilder.build_storage(
                StorageType.LocalStorage,
                storage_path,
                True
            )
            ))
        except Exception as e:
            st.error(f"Error creating knowledge warehouse: {str(e)}")
            return False

        # Clean up temp files
        delete_temp_files(file_paths)

        # Save knowledge warehouse
        save_knowledge_warehouse(kw)

        st.session_state[knowledge_warehouses_key][kw.kw_id] = kw
        st.session_state[selected_knowledge_warehouse_key] = kw
    
        return True
    except Exception as e:
        st.error(f"Error creating knowledge warehouse: {str(e)}")
        return False

def render_knowledge_warehouse_admin():
    st.title("Knowledge Warehouse Administration")

    # Create new knowledge warehouse
    with st.expander("Create New Knowledge Warehouse", expanded=True):
        with st.form("new_kw_form"):
            kw_name = st.text_input("Knowledge Warehouse Name")
            # storage_path = st.text_input("Storage Path", value="./knowledge_warehouse_storage")
            storage_path = os.path.join(os.getenv("LOCAL_KNOWLEDGE_WAREHOUSE_STORAGE_PATH"), st.session_state.login_user_id)
            uploaded_files = st.file_uploader(
                "Upload Knowledge Files", 
                accept_multiple_files=True,
                type=["txt", "pdf", "doc", "docx", "csv"]
            )
            
            submit = st.form_submit_button("Create Knowledge Warehouse")
            
            if submit and kw_name and uploaded_files:
                os.makedirs(storage_path, exist_ok=True)
                if create_knowledge_warehouse(kw_name, uploaded_files, storage_path):
                    st.success(f"Successfully created knowledge warehouse: {kw_name}")

    # List existing knowledge warehouses
    st.subheader("Existing Knowledge Warehouses")
    for kw_id, kw in st.session_state[knowledge_warehouses_key].items():
        with st.expander(f"📚 {kw.name}"):
            kw.print_info()
            
            # Add new files to existing warehouse
            uploaded_files = st.file_uploader(
                "Add More Files",
                accept_multiple_files=True,
                type=["txt", "pdf", "doc", "docx", "csv"],
                key=f"add_files_{kw.name}"
            )
            
            if uploaded_files:
                file_paths = upload_to_temp_dir(uploaded_files)
                    
                for path in file_paths:
                    kw.add_file(path)

                # Clean up temp files
                delete_temp_files(file_paths)

                # Save knowledge warehouse
                save_knowledge_warehouse(kw)
                
                st.success(f"Successfully added files to {kw.name}")

# if __name__ == "__main__":
#     render_knowledge_warehouse_admin()
