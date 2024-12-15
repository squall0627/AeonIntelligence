import os

# Path to your Streamlit app script
app_path = "app.py"

# Port to run Streamlit on
port = os.environ.get("PORT", 8502)

# Command to launch Streamlit
os.system(f"streamlit run {app_path} --server.port={port} --server.address=0.0.0.0")
