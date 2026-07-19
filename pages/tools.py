import os
import tempfile

import streamlit as st

from services.transcriber import transcribe_audio
from services.llm_client import transcription_cleanup

st.title("Tools")

st.header("Transcribe Audio File")

live_recording = st.audio_input(label="Record a voice message", sample_rate=16000)

if live_recording:
    st.audio(live_recording, sample_rate=16000)

mode_choice = st.selectbox(
    "Select the processing mode",
    options=["Transcription Cleanup", "Note Taking"],
    help="Choose how to process the uploaded audio file."
)

if st.button("Transcribe"):
    if not live_recording:
        st.warning("No audio input detected. Please record a voice message to transcribe.")
        st.stop()

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(live_recording.read())
            tmp_path = tmp.name

        with st.spinner("Transcribing audio..."):
            transcription, _ = transcribe_audio(tmp_path)
        st.text_area("Transcription:", value=transcription, height=200)

        with st.spinner("Cleaning up transcription..."):
            cleaned_transcription = transcription_cleanup(transcription, mode_choice=mode_choice)
        st.text_area("Post LLM Cleanup:", value=cleaned_transcription, height=200)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
