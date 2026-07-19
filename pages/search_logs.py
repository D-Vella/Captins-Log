import streamlit as st
from services.database import search_logs_by_keyword

st.title("Search Logs")
keyword = st.text_input("Enter keywords to search for")

if st.button("Search"):
    if not keyword.strip():
        st.warning("Please enter a keyword to search.")
        st.stop()
    # Call the search function and display results
    with st.spinner("Searching..."):
        results = search_logs_by_keyword(keyword)

    if not results:
        st.info(f"No log entries found matching '{keyword}'.")
        st.stop()

    for idx, entry in enumerate(results):
        with st.expander(f"{entry['entry_date']} (Entry ID: {entry['id']})"):
            tab_log, tab_transcript = st.tabs(["Log", "Transcript"])
            with tab_log:
                st.write(entry['formatted_md'])
            with tab_transcript:
                st.text_area("Transcript", value=entry['raw_transcript'],
                             height=200, key=f"search-transcript-{idx}")
