import streamlit as st
import services.controller as ctrl
from datetime import date

def log_history():
    st.title("Log History")
    
    try:
        from services.database import api_get_logs
        
        logs = api_get_logs("")
        
        if logs:
            for entry in logs.values():
                with st.expander(entry["entry_date"]):
                    import pathlib
                    LOGS_DIR = pathlib.Path(__file__).parent.parent / "data" / "logs"
                    log_file = LOGS_DIR / f"{entry['entry_date']}.md"
                    if log_file.exists():
                        st.markdown(log_file.read_text(encoding="utf-8"))
                    else:
                        st.caption("Markdown file not found for this entry.")
        else:
            st.info("No log entries in the database yet.")
    
    except Exception as e:
        st.exception(e)

if __name__ == "__main__":
    log_history()