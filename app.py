import streamlit as st
from datetime import date
import pathlib

# st.set_page_config must be the first Streamlit call in the file.
st.set_page_config(
    page_title="Captain's Log",
    layout="wide"
)

ROOT_DIR = pathlib.Path(__file__).parent
LOGS_DIR = ROOT_DIR / "data" / "logs"

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("Captain's Log")
page = st.sidebar.radio("Navigate", ["Record", "Today's Log", "Log History", "Weekly Review"])

# ---------------------------------------------------------------------------
# RECORD
# ---------------------------------------------------------------------------
if page == "Record":
    st.title("New Recording")
    st.caption("Upload an audio file to transcribe and log.")

    uploaded_file = st.file_uploader(
        "Choose an audio file",
        type=["wav", "m4a", "mp3"],
        help="Recordings made on your phone or with cli/record.py both work here."
    )

    if uploaded_file:
        st.audio(uploaded_file)

        if st.button("Process recording"):
            # Replace this block with the real pipeline once wired up:
            #
            # import tempfile, os
            # from services import transcriber, llm_client, database
            #
            # with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            #     tmp.write(uploaded_file.read())
            #     tmp_path = tmp.name
            #
            # with st.spinner("Transcribing..."):
            #     transcript, duration = transcriber.transcribe_audio(tmp_path)
            #
            # with st.spinner("Formatting with LLM..."):
            #     markdown_out = llm_client.llm_formatter(transcript)
            #
            # with st.spinner("Generating follow-up questions..."):
            #     questions = llm_client.llm_question_generator(markdown_out)
            #
            # today = date.today().isoformat()
            # entry_id = database.create_or_get_log_header(today)
            # database.create_log_segment(entry_id, uploaded_file.name, duration, transcript)
            # database.create_log_enrichment(entry_id, markdown_out, questions)
            #
            # LOGS_DIR.mkdir(parents=True, exist_ok=True)
            # log_file = LOGS_DIR / f"{today}.md"
            # with open(log_file, "w", encoding="utf-8") as f:
            #     f.write(markdown_out)
            #     f.write(f"\n\n## Follow-up questions\n\n{questions}")
            #
            # st.success("Done! Switch to Today's Log to see the result.")

            st.info("Pipeline not wired up yet — see the commented block above in app.py.")

# ---------------------------------------------------------------------------
# TODAY'S LOG
# ---------------------------------------------------------------------------
elif page == "Today's Log":
    today = date.today().isoformat()
    st.title(f"Today's Log — {today}")

    log_file = LOGS_DIR / f"{today}.md"

    if log_file.exists():
        st.markdown(log_file.read_text(encoding="utf-8"))
    else:
        st.info(f"No entry for {today} yet. Head to Record to create one.")

# ---------------------------------------------------------------------------
# LOG HISTORY
# ---------------------------------------------------------------------------
elif page == "Log History":
    st.title("Log History")

    try:
        from services.database import api_get_logs

        logs = api_get_logs("")

        if logs:
            for entry in logs.values():
                with st.expander(entry["entry_date"]):
                    log_file = LOGS_DIR / f"{entry['entry_date']}.md"
                    if log_file.exists():
                        st.markdown(log_file.read_text(encoding="utf-8"))
                    else:
                        st.caption("Markdown file not found for this entry.")
        else:
            st.info("No log entries in the database yet.")

    except Exception as e:
        st.error(f"Could not load logs: {e}")

# ---------------------------------------------------------------------------
# WEEKLY REVIEW
# ---------------------------------------------------------------------------
elif page == "Weekly Review":
    st.title("Weekly Review")
    st.caption("Generate a summary of this week's entries. (Phase 8)")

    if st.button("Generate this week's review"):
        # Replace with the real pipeline once wired up:
        #
        # from services import llm_client, database
        # with st.spinner("Asking the LLM for a weekly summary..."):
        #     summary = llm_client.llm_weekly_reviewer(...)
        # st.markdown(summary)

        st.info("Weekly review not wired up yet — see the commented block above in app.py.")
