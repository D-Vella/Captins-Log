import streamlit as st


# Set page config must be the first Streamlit call
st.set_page_config(page_title="Captain's Log", layout="wide")

# Sidebar navigation
with st.sidebar:
    st.sidebar.title("Captain's Log")
    pages = [
        st.Page("pages/todays_log.py", title="Today's Log")
    ]
