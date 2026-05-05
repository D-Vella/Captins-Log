"""
Log History: 
This page displays a chronological list of all log entries stored in the database. 
It iterates through the available entries, showing a collapsible section (expander) 
for each date, and attempts to render the associated markdown file for detailed viewing.
"""
import streamlit as st
import services.controller as ctrl
from datetime import date

st.title("Log History")

try:
    from services.database import api_get_logs

    logs = api_get_logs("")

    if logs:
        for entry in logs.values():
            with st.expander(entry["entry_date"]):
                import pathlib
                LOGS_DIR = pathlib.Path(__file__).parent.parent / "data" / "logs"
                log_file = LOGS_DIR / f"{entry['entry_date']}.md"
                if log_file.exists():
                    st.markdown(log_file.read_text(encoding="utf-8"))
                else:
                    st.caption("Markdown file not found for this entry.")
    else:
        st.info("No log entries in the database yet.")

except Exception as e:
    st.exception(e)
