"""
Today's Log: 
This page displays the log entries for the current date. 
It reads the markdown file corresponding to today's date from the 'data/logs' directory 
and renders the content for immediate viewing.
"""
import streamlit as st
from services.config import LOGS_DIR
from datetime import date

st.title(f"Today's Log:")

today = date.today().isoformat()
log_file = LOGS_DIR / f"{today}.md"

if log_file.exists():
    st.markdown(log_file.read_text(encoding="utf-8"))
else:
    st.info(f"No entry for {today} yet. Head to Record to create one.")