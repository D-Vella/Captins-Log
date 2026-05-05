"""
Weekly Review: 
This page allows users to generate a structured summary of log entries across a specified 
date range (a week). It interacts with the controller to use the LLM for summarizing 
the collected data from the week.
"""
import streamlit as st
import services.controller as ctrl
from datetime import date, timedelta

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
        with st.spinner("Asking the LLM for a weekly summary..."):
            start_date, end_date = date_range
            summary = ctrl.weekly_review(start_date, end_date)
        st.markdown(summary)