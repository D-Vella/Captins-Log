"""
New Log Recording: 
This page serves as the dedicated interface for creating new log entries. 
Users upload an audio file, which is then processed by the controller to transcribe 
and save the log entry, making it available on the Today's Log page.
"""
import streamlit as st
import services.controller as ctrl
from typing import cast
from streamlit.runtime.uploaded_file_manager import UploadedFile

st.title("Record a new log entry")

st.header("Live Recording",divider=True)
live_recording = st.audio_input(label="Record a voice message", sample_rate=16000)

if live_recording:
    st.audio(live_recording, sample_rate=16000)


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
    import tempfile, os
    from datetime import date
        
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        # Cast to UploadedFile to satisfy type checker
        if live_recording:
            file = cast(UploadedFile, live_recording)
        else:
            file = cast(UploadedFile, uploaded_file)
        tmp.write(file.read())
        tmp_path = tmp.name
        
    ctrl.process_log_entry(tmp_path, date.today().strftime("%Y-%m-%d"))
    
    #st.success("Done! Switch to Today's Log to see the result.")
    st.cache_data.clear()  # Clear cache to ensure new entry is loaded  
    st.switch_page("pages/todays_log.py")