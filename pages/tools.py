import streamlit as st
from services.transcriber import transcribe_audio
from services.llm_client import transcription_cleanup
import tempfile

st.title("Tools")

st.header("Transcribe Audio File")

live_recording = st.audio_input(label="Record a voice message", sample_rate=16000)

if live_recording:
    st.audio(live_recording, sample_rate=16000)

if st.button("Transcribe"):
    if live_recording:
        file = live_recording
    else:
        st.warning("No audio input detected. Please record a voice message to transcribe.")
        st.stop()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name
    
    with st.spinner("Transcribing audio..."):
        transcription, _ = transcribe_audio(tmp_path)
        st.text_area("Transcription:", value=transcription, height=200)
        with st.spinner("Cleaning up transcription..."):
            cleaned_transcription = transcription_cleanup(transcription)
        st.text_area("Post LLM Cleanup:", value=cleaned_transcription, height=200)

    st.cache_data.clear()
