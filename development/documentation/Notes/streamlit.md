# Streamlit — Beginner's Guide for This Project

Streamlit is a Python library that turns a regular `.py` script into an interactive web app. You write Python, Streamlit renders the browser UI. No HTML, no JavaScript, no separate server code.

---

## Installation

```bash
pip install streamlit streamlit-audiorecorder
```

Verify it works:

```bash
streamlit hello
```

This opens a demo app in your browser. Close it with `Ctrl+C` in the terminal.

---

## Running the app

From the project root (where `app.py` lives):

```bash
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`. Every time you save `app.py`, the browser reloads and picks up your changes — no restart needed.

---

## The most important thing to understand: reruns

**Every time a user interacts with a widget, Streamlit reruns the entire script from top to bottom.**

This is the central idea. It means:

```python
# This runs again from scratch on every button click, slider move, file upload, etc.
import streamlit as st

name = st.text_input("Your name")   # widget captures current value
st.write(f"Hello, {name}")          # immediately reflects the current value
```

The upside is simplicity — there are no callbacks, no event handlers, no component state to manage. The downside is that anything expensive (a database query, an LLM call) runs again on every rerun unless you protect it.

---

## Protecting expensive operations: session_state and caching

### `st.session_state`

A dictionary that persists across reruns within the same browser session. Use it to hold results you only want to compute once:

```python
if "transcript" not in st.session_state:
    st.session_state.transcript = None

if st.button("Transcribe"):
    with st.spinner("Transcribing..."):
        st.session_state.transcript = transcriber.transcribe_audio(path)

if st.session_state.transcript:
    st.write(st.session_state.transcript)
```

Without `session_state`, clicking "Transcribe" would rerun the script and lose the result immediately.

### `@st.cache_data`

For functions that return data (database queries, file reads). Streamlit skips re-running the function if the arguments haven't changed:

```python
@st.cache_data
def load_log_history():
    return database.api_get_logs("")

logs = load_log_history()   # cached after first call
```

---

## Displaying content

| What you want | Function |
|---------------|----------|
| Plain text | `st.write("hello")` |
| Markdown | `st.markdown("# Heading\n- item")` |
| Code block | `st.code("SELECT * FROM log_entry", language="sql")` |
| JSON | `st.json({"key": "value"})` |
| Audio player | `st.audio(file_bytes_or_path)` |
| Success / info / warning / error banners | `st.success("Done")`, `st.info(...)`, `st.warning(...)`, `st.error(...)` |
| Loading spinner | `with st.spinner("Working..."):` |

---

## Widgets (inputs)

Every widget returns its current value. You use the return value directly — no callbacks needed.

```python
name   = st.text_input("Name")                     # str
age    = st.number_input("Age", min_value=0)        # float
agree  = st.checkbox("I agree")                     # bool
choice = st.radio("Pick one", ["A", "B", "C"])      # str
file   = st.file_uploader("Upload", type=["wav"])   # UploadedFile or None
clicked = st.button("Go")                           # bool (True only on the rerun after the click)
```

---

## Layout

### Columns

```python
col1, col2 = st.columns(2)

with col1:
    st.write("Left side")

with col2:
    st.write("Right side")
```

### Sidebar

```python
choice = st.sidebar.radio("Page", ["Record", "History"])
```

The sidebar stays visible across all pages.

### Expanders (collapsible sections)

```python
with st.expander("2024-06-02"):
    st.markdown("Entry content here...")
```

Useful for the Log History page where you want to show many entries without overwhelming the screen.

---

## Multi-page apps

For larger apps, Streamlit supports a `pages/` folder. Each `.py` file in it becomes a separate page with its own sidebar entry:

```
app.py          ← entry point (shown as first page)
pages/
    1_Record.py
    2_Today's_Log.py
    3_Log_History.py
    4_Weekly_Review.py
```

Run the same way: `streamlit run app.py`. Streamlit discovers the `pages/` folder automatically.

The current `app.py` uses a single-file sidebar radio approach — easier to follow while learning. Splitting into `pages/` is a straightforward refactor once the logic is working.

---

## Testing the app

### Manual testing (the main method)

Run the app and interact with it in the browser. Because the whole script re-executes on every interaction, most bugs surface immediately.

```bash
streamlit run app.py
```

Things to check on each page:
- **Record**: upload a small audio file, confirm `st.audio` renders a player, confirm the "Process" button shows the placeholder message
- **Today's Log**: if `data/logs/YYYY-MM-DD.md` exists for today, confirm it renders; if not, confirm the info message appears
- **Log History**: confirm entries from the database appear in expanders; test with an empty DB too (the `try/except` should show an error banner rather than crashing)
- **Weekly Review**: confirm the button triggers the placeholder message

### Testing service logic separately

The services (`transcriber.py`, `llm_client.py`, `database.py`) are plain Python functions. Test them independently in a notebook or a short script — there is no need to go through the Streamlit UI to test service logic:

```python
# quick_test.py
from services.database import api_get_logs
print(api_get_logs(""))
```

```bash
python quick_test.py
```

This is faster than going through the UI for every change to a service function.

### Checking for rerun side-effects

A common Streamlit bug: a function that should run once runs on every rerun because it isn't guarded by `if st.button(...)` or `st.session_state`. If something runs unexpectedly on page load, look for code that isn't inside a widget conditional or cached.

---

## Useful patterns for this project

**Saving an uploaded file to a temp location for Faster-Whisper:**

```python
import tempfile, os

uploaded = st.file_uploader("Audio", type=["wav", "m4a", "mp3"])
if uploaded:
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(uploaded.name)[1], delete=False) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name
    # pass tmp_path to transcriber.transcribe_audio(tmp_path)
```

**Showing a multi-step progress sequence:**

```python
if st.button("Process"):
    with st.spinner("Transcribing..."):
        transcript, duration = transcriber.transcribe_audio(tmp_path)
    st.session_state.transcript = transcript
    st.success("Transcription complete")

    with st.spinner("Formatting with LLM..."):
        markdown_out = llm_client.llm_formatter(transcript)
    st.session_state.markdown_out = markdown_out

    st.markdown(markdown_out)
```

**Rendering today's log or a fallback:**

```python
from datetime import date
import pathlib

log_file = pathlib.Path("data/logs") / f"{date.today().isoformat()}.md"
if log_file.exists():
    st.markdown(log_file.read_text(encoding="utf-8"))
else:
    st.info("No entry for today yet.")
```

---

## Further reading

- [Streamlit docs](https://docs.streamlit.io) — clear and well-organised, start with "Get started"
- [Streamlit cheat sheet](https://docs.streamlit.io/develop/quick-reference/cheat-sheet) — one-page reference for all widgets and display functions
- [session_state docs](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
- [st.cache_data docs](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)
