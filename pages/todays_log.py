"""
Today's Log: 
This page displays the log entries for the current date. 
It reads the markdown file corresponding to today's date from the 'data/logs' directory 
and renders the content for immediate viewing.
"""
import streamlit as st
import services.controller as ctrl
from datetime import date
import pathlib

st.title(f"Today's Log:")

LOGS_DIR = pathlib.Path(__file__).parent.parent / "data" / "logs"
today = date.today().isoformat()
log_file = LOGS_DIR / f"{today}.md"

if log_file.exists():
    st.markdown(log_file.read_text(encoding="utf-8"))
else:
    st.info(f"No entry for {today} yet. Head to Record to create one.")