"""
Log History: 
This page displays a chronological list of all log entries stored in the database. 
It iterates through the available entries, showing a collapsible section (expander) 
for each date, and attempts to render the associated markdown file for detailed viewing.
"""
import streamlit as st
from services.config import LOGS_DIR, RECORDINGS_DIR
import os
from services.database import api_get_logs, get_dated_entry_id, get_unified_transcripts

st.title("Log History")

try:
    logs = api_get_logs("")

    if logs:
        for entry in logs.values():
            with st.expander(entry["entry_date"]):
                log_file = LOGS_DIR / f"{entry['entry_date']}.md"
                st.download_button(
                    label="Download Markdown",
                    data=log_file.read_bytes(),
                    file_name=f"{entry['entry_date']}.md",
                    mime="text/markdown"
                )
                with st.expander("View log data"):
                    with st.expander("Audio Recordings"):
                        log_recordings = [x for x in os.listdir(RECORDINGS_DIR) if x.startswith(entry["entry_date"])]
                        for idx, recording in enumerate(log_recordings):
                            st.subheader(f"Recording {idx+1}")
                            st.audio(RECORDINGS_DIR / recording)
                    with st.expander("Transcript"):
                        log_id = get_dated_entry_id(entry["entry_date"])
                        transcript = get_unified_transcripts(log_id)
                        st.text_area("Transcript", value=transcript, height=200)
                if log_file.exists():
                    st.markdown(log_file.read_text(encoding="utf-8"))
                else:
                    st.caption("Markdown file not found for this entry.")
    else:
        st.info("No log entries in the database yet.")

except Exception as e:
    st.exception(e)
