import streamlit as st
from services.database import search_logs_by_keyword

st.title("Search Logs")
keyword = st.text_input("Enter keywords to search for")

if st.button("Search"):
    if not keyword.strip():
        st.warning("Please enter a keyword to search.")
        st.stop()
    # Call the search function and display results
    st.spinner("Searching...")
    results = search_logs_by_keyword(keyword)

    if not results:
        st.info(f"No log entries found matching '{keyword}'.")
        st.stop()

    for entry in results:
        st.write(f"Entry ID: {entry['id']}, Date: {entry['entry_date']}")
        with st.expander(entry['entry_date']):
            with st.expander("Transcript"):
                st.text_area("Transcript", value=entry['raw_transcript'], height=200)
            st.write(entry['formatted_md'])
