"""
New Log Recording: 
This page serves as the dedicated interface for creating new log entries. 
Users upload an audio file, which is then processed by the controller to transcribe 
and save the log entry, making it available on the Today's Log page.
"""
import os
import tempfile
from datetime import date

import streamlit as st

import services.controller as ctrl
from services.config import LOGS_DIR

st.title("Record a new log entry")

col_controls, col_tips = st.columns(2)

with col_controls:
    st.header("Date of entry",divider=True)
    entry_date = st.date_input("Select the date for this log entry", value=date.today())
    st.header("Live Recording",divider=True)
    live_recording = st.audio_input(label="Record a voice message", sample_rate=16000)

    if live_recording:
        st.audio(live_recording, sample_rate=16000)

    with st.expander("Upload a recording"):
        st.header("Upload a recording",divider=True)
        st.caption("Upload an audio file to transcribe and log.")

        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=["wav", "m4a", "mp3"],
            help="Recordings made on your phone or with cli/record.py both work here."
        )

        if uploaded_file:
            st.audio(uploaded_file)

    if st.button("Process recording"):
        audio = live_recording or uploaded_file
        if audio is None:
            st.error("Please record a voice message or upload a file first.")
            st.stop()

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio.read())
                tmp_path = tmp.name

            progress_bar = st.progress(0, text="Starting transcription...")
            def update_progress(percent, message):
                progress_bar.progress(percent, text=message)
            ctrl.process_log_entry(tmp_path, entry_date.strftime("%Y-%m-%d"), on_progress=update_progress)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        st.cache_data.clear()  # Clear cache to ensure new entry is loaded
        st.switch_page("pages/todays_log.py")

    # Display today's log entry if it exists
    st.header("Today's log entry",divider=True)
    today = date.today().isoformat()
    log_file = LOGS_DIR / f"{today}.md"

    if log_file.exists():
        st.markdown(log_file.read_text(encoding="utf-8"))
    else:
        st.info(f"No entry for {today} yet. Head to Record to create one.")

with col_tips:
    st.divider()
    st.header("Suggested topics:")
    st.markdown("""
                * Energy — How does my body/mind feel compared to yesterday?
                * The standout moment — What's the one thing I'd tell a friend about today?
                * Friction — What frustrated me, slowed me down, or felt off?
                * Small win — What went better than expected, even slightly?
                * Unfinished thought — What's been quietly sitting in the back of my mind?
                * Tomorrow's intention — What's the one thing I want to carry into tomorrow?
                * Things to do - What do I need to do tomorrow? What am I procrastinating on?
                """)
    st.divider()
    st.header("The post work topics:")
    st.markdown("""
                ### Active Thoughts:
                * What am I still thinking about?
                * What is unfinished?
                * What desisions am I still mulling over?

                ### Tomorrow's Priorities:
                * What are the 1-3 most important things to do tomorrow?
                * Anything time sensitive or politically sensitive coming up?

                ### Worries or anxieties:
                * List of anything in my head that is causing stress or worry.

                ### What went well:
                * What jobs have I completed?
                * Success stories
                * Items for recognition friday
                
                ### Explicit clouse out:
                * Is there anything else I want to say to myself before I close out the day?
                
                """)