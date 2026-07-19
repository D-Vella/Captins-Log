"""
Log History:
This page displays a chronological list of all log entries stored in the database.
It iterates through the available entries, showing a collapsible section (expander)
for each date, with tabs for the formatted log, the raw transcript, and the audio.
"""
import os

import streamlit as st

from services.config import LOGS_DIR, RECORDINGS_DIR
from services.database import api_get_logs, get_unified_transcripts

st.title("Log History")

logs = api_get_logs("")

if not logs:
    st.info("No log entries in the database yet.")

for entry in logs.values():
    entry_date = entry["entry_date"]
    with st.expander(entry_date):
        tab_log, tab_transcript, tab_audio = st.tabs(["Log", "Transcript", "Audio"])

        with tab_log:
            log_file = LOGS_DIR / f"{entry_date}.md"
            if log_file.exists():
                st.download_button(
                    label="Download Markdown",
                    data=log_file.read_bytes(),
                    file_name=f"{entry_date}.md",
                    mime="text/markdown",
                    key=f"download-{entry_date}"
                )
                st.markdown(log_file.read_text(encoding="utf-8"))
            else:
                st.caption("Markdown file not found for this entry.")

        with tab_transcript:
            transcript = get_unified_transcripts(entry["id"])
            st.text_area("Transcript", value=transcript, height=200,
                         key=f"transcript-{entry_date}")

        with tab_audio:
            if RECORDINGS_DIR.exists():
                log_recordings = sorted(x for x in os.listdir(RECORDINGS_DIR)
                                        if x.startswith(entry_date))
            else:
                log_recordings = []

            if not log_recordings:
                st.caption("No recordings found for this entry.")

            for idx, recording in enumerate(log_recordings):
                st.subheader(f"Recording {idx+1}")
                st.audio(RECORDINGS_DIR / recording)
