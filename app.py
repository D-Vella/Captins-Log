import streamlit as st

from alembic.config import Config
from alembic import command

def init_database():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

# Set page config must be the first Streamlit call
st.set_page_config(page_title="Captain's Log", layout="wide")

# Sidebar navigation
with st.sidebar:
    st.sidebar.title("Captain's Log")
    pages = [
        st.Page("pages/todays_log.py", title="Today's Log")
    ]
