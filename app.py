import streamlit as st
from datetime import date, timedelta
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
page = st.sidebar.radio("Navigate", ["Record", "Today's Log", "Log History", "Weekly Review", "Admin Panel"])

# ---------------------------------------------------------------------------
# Page Functions (to be moved to own pages later)
# ---------------------------------------------------------------------------
def new_log():
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

def todays_log():

    today = date.today().isoformat()
    st.title(f"Today's Log — {today}")

    log_file = LOGS_DIR / f"{today}.md"

    if log_file.exists():
        st.markdown(log_file.read_text(encoding="utf-8"))
    else:
        st.info(f"No entry for {today} yet. Head to Record to create one.")

def log_history():
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
        st.exception(e)
        #st.error(f"Could not load logs: {e}")

def weekly_review():
    from services.database import get_weekly_transcripts
    st.title("Weekly Review")
    st.caption("Generate a summary of this week's entries.")

    date_range = st.date_input(
        "Select week",
        value=(
            date.today() - timedelta(days=7),
            date.today()
        )
    )

    if st.button("Generate this week's review"):
        if len(date_range) == 2:
            start_date, end_date = date_range
            transcripts = get_weekly_transcripts(start_date, end_date)
            #st.text(transcripts)

            from services import llm_client, database
            with st.spinner("Asking the LLM for a weekly summary..."):
                summary = llm_client.weekly_review(transcripts)
            st.markdown(summary)
        else:
            st.info("Weekly review not wired up yet — see the commented block above in app.py.")

def admin_panel():

    import pandas as pd
    from services.database import (
        api_get_logs,
        api_get_segments,
        api_get_enrichments,
        api_delete_log_entry
    )

    st.info("Currently implementing.")
    # region ── Session State ─────────────────────────────────
    if "admin_selected_entry" not in st.session_state:
        st.session_state.admin_selected_entry = None

    if "admin_confirm_delete" not in st.session_state:
        st.session_state.admin_confirm_delete = False
    # endregion

    # region ── Data Loaders ───────────────────────────────────
    @st.cache_data
    def load_headers():
        return api_get_logs("")

    @st.cache_data
    def load_segments():
        return api_get_segments()

    @st.cache_data
    def load_enrichments():
        return api_get_enrichments()
    # endregion

    # region ── Render Functions ───────────────────────────────
    def render_overview(headers, segments, enrichments):
        st.subheader("Database Overview")

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.metric("Log Entries", len(headers))

        with col_b:
            st.metric("Segments", len(segments))

        with col_c:
            st.metric("Enrichments", len(enrichments))

        if headers:
            dates = sorted(headers.keys())
            st.caption(f"Earliest entry: {dates[0]}  |  Latest entry: {dates[-1]}")

        st.divider()


    def render_table_viewer(headers, segments, enrichments):
        st.subheader("Table Viewer")

        table_choice = st.selectbox(
            "Select table",
            ["Log Headers", "Segments", "Enrichments"]
        )

        if table_choice == "Log Headers":
            data = list(headers.values()) if headers else []
        elif table_choice == "Segments":
            data = segments if segments else []
        else:
            data = enrichments if enrichments else []

        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("No records found in this table.")

        st.divider()


    def render_entry_management(headers):
        st.subheader("Entry Management")

        if not headers:
            st.info("No entries in the database.")
            return

        selected_date = st.selectbox(
            "Select entry to manage",
            options=sorted(headers.keys(), reverse=True),
            index=None,
            placeholder="Choose a date..."
        )

        if selected_date:
            st.session_state.admin_selected_entry = selected_date
            entry = headers[selected_date]

            st.write(f"**Date:** {entry['entry_date']}")

            if st.button("Delete Entry", type="secondary"):
                st.session_state.admin_confirm_delete = True

        if st.session_state.admin_confirm_delete:
            st.warning(
                f"Are you sure you want to delete the entry for "
                f"**{st.session_state.admin_selected_entry}** and all associated "
                f"segments and enrichments? This cannot be undone."
            )

            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button("Yes, delete it", type="primary"):
                    api_delete_log_entry(st.session_state.admin_selected_entry)
                    st.cache_data.clear()
                    st.session_state.admin_confirm_delete = False
                    st.session_state.admin_selected_entry = None
                    st.success("Entry deleted.")
                    st.rerun()

            with col_cancel:
                if st.button("Cancel"):
                    st.session_state.admin_confirm_delete = False
                    st.rerun()
    # endregion

    # region ── Page ───────────────────────────────────────────
    st.title("Admin")
    st.caption("Database management and diagnostics.")

    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()

    headers = load_headers()
    segments = load_segments()
    enrichments = load_enrichments()

    render_overview(headers, segments, enrichments)
    render_table_viewer(headers, segments, enrichments)
    render_entry_management(headers)
    
# ---------------------------------------------------------------------------
# Table Of contents:
# ---------------------------------------------------------------------------
if page == "Record":
    new_log()
elif page == "Today's Log":
    todays_log()
elif page == "Log History":
    log_history()
elif page == "Weekly Review":
    weekly_review()
elif page == "Admin Panel":
    admin_panel()
