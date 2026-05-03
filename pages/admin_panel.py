import streamlit as st
import pandas as pd
from services.database import (
    api_get_logs,
    api_get_segments,
    api_get_enrichments,
    api_delete_log_entry
)
from typing import cast

def admin_panel():
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

if __name__ == "__main__":
    admin_panel()