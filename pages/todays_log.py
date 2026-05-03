import streamlit as st
import services.controller as ctrl
from datetime import date
import pathlib

def todays_log():
    today = date.today().isoformat()
    st.title(f"Today's Log — {today}")
    
    LOGS_DIR = pathlib.Path(__file__).parent.parent / "data" / "logs"
    log_file = LOGS_DIR / f"{today}.md"
    
    if log_file.exists():
        st.markdown(log_file.read_text(encoding="utf-8"))
    else:
        st.info(f"No entry for {today} yet. Head to Record to create one.")

if __name__ == "__main__":
    todays_log()