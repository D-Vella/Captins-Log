# Learning Points

A running log of issues encountered during development, with explanations and teaching points.

---

## Session 1 — 2026-04-21

---

### 1. `dict.get()` requires a string key, not a list

**The bug:**
```python
returnMessage.get(['response'], '')  # passes a list as the key
```

**The fix:**
```python
returnMessage.get('response', '')
```

**Why it matters:**  
`dict.get(key, default)` looks up a key in a dictionary. The key must match the type used when the dict was created — in JSON responses, keys are always strings. Passing `['response']` creates a list object as the key, which will never match any string key, so `.get()` always returns the default (`''`).

---

### 2. Typos in dictionary keys are silent failures

**The bug:**
```python
payload = {
    "mesages": [...]  # missing an 's'
}
```

**Why it matters:**  
Python won't raise an error for a misspelled key — it just creates a key with the wrong name. The Ollama API silently ignored the unrecognised field and returned an empty response. This class of bug produces no traceback, making it hard to spot. Always check the API documentation for exact key names.

---

### 3. Different API endpoints use different response shapes

**The bug:**  
The code used `returnMessage.get('response', '')` but was calling the `/api/chat` endpoint, not `/api/generate`.

**The fix:**
```python
returnMessage.get('message', {}).get('content', '')
```

**Why it matters:**  
Ollama's `/api/generate` returns `{"response": "..."}` but `/api/chat` returns `{"message": {"role": "assistant", "content": "..."}}`. Always check the specific endpoint's response schema — don't assume two endpoints on the same service return the same shape.

---

### 4. `== None` vs `is None` vs `not x`

**The bug:**
```python
if markdown_response == None:   # misses empty string
```

**The fix:**
```python
if not markdown_response:       # catches None, '', [], 0
```

**Why it matters:**  
In Python, `== None` only catches `None` exactly. An empty string `''` is falsy but is not `None`, so `'' == None` is `False` and the guard is bypassed. The idiomatic way to check for "nothing useful here" is `if not x`, which catches `None`, empty strings, empty lists, and zero. Use `is None` only when you specifically need to distinguish `None` from other falsy values.

---

### 5. Variables assigned only inside a `try` block can be unbound

**The bug:**
```python
try:
    question_text = ""
    ...
except:
    print("Issue with LLM response.")

return question_text  # crashes if the try block failed
```

**The fix:**  
Either initialise the variable before the `try` block, or `raise` inside the `except` so the function never reaches the `return`.

**Why it matters:**  
Python determines whether a variable exists at runtime, not at parse time. If the `try` block raises before `question_text` is assigned, Python has no value for it, and `return question_text` raises `UnboundLocalError`. The safest pattern is to initialise variables to a sensible default before any block that might not run.

---

### 6. `if / if` vs `if / else` — both branches can evaluate

**The bug:**
```python
if log_id == None:
    result = session.execute(...).fetchall()

if len(log_id) > 0:             # also evaluates when log_id is None → crash
    result = session.execute(...).fetchone()
```

**The fix:**
```python
if log_id is None:
    result = session.execute(...).fetchall()
else:
    result = session.execute(...).fetchone()
```

**Why it matters:**  
Two separate `if` statements are both evaluated independently. When `log_id` is `None`, the first `if` runs correctly, but Python then hits the second `if` and tries to call `len(None)`, which crashes. `if / else` guarantees only one branch runs.

---

### 7. `.count` on a SQLAlchemy row is a method, not a property

**The bug:**
```python
elif result.count == 0:   # always False — comparing a method object to 0
```

**Why it matters:**  
`result.count` without parentheses returns the method object itself, which is always truthy and never equal to `0`. This is a common Python gotcha — forgetting `()` means you're referencing the function rather than calling it. In this case the right fix was to use `if not result:` instead, which handles empty lists and `None` cleanly.

---

### 8. Relative database paths break when the working directory changes

**The bug:**
```python
DATABASE_URL = "sqlite:///../db/application.db"
```

This worked in the Jupyter notebook (run from `cli/`) but failed when uvicorn was launched from the project root.

**The fix:**
```python
import os
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{_BASE_DIR}/db/application.db"
```

**Why it matters:**  
Relative paths resolve from the **current working directory** at the time the code runs, not from the file's location. As soon as you run your code from a different directory (e.g. launching uvicorn from the project root instead of `cli/`), relative paths break. Anchoring paths to `__file__` (the location of the source file itself) makes them reliable regardless of where the process is started.

---

### 9. `fetchone()` and `fetchall()` return different types

**The bug:**  
The same loop was used to process both results:
```python
for idx, current_result in enumerate(results):
    result['id'] = current_result[0]   # works for fetchall, breaks for fetchone
```

**Why it matters:**  
- `fetchall()` returns a **list of rows** — iterating gives you one row per iteration, so `current_result[0]` is the first column of that row.  
- `fetchone()` returns a **single row** — iterating over it gives you individual column *values*, so `current_result` would be an integer or string, and `current_result[0]` either crashes or gives the wrong thing.

Always handle these two cases separately, or use `fetchall()` for both (a single-row query will just return a list of length 1).

---

### 10. `datetime` objects are not JSON serialisable by default


**The bug:**  
Returning a dict containing a `datetime` object through `json.dumps()` raises a `TypeError`.

**The fix:**
```python
'created_at': str(row[2])   # convert to ISO string before serialising
```

**Why it matters:**  
Python's `json` module only knows how to serialise basic types: strings, numbers, lists, dicts, booleans, and `None`. Any other type — `datetime`, `Decimal`, SQLAlchemy Row objects, etc. — must be converted manually before calling `json.dumps()`. A quick `str()` works for datetimes; for more control use `.isoformat()`.

---

## Session 2 — 2026-05-01

---

### 11. Unsaved files are invisible to the running program (and to other tools)

**The situation:**  
Three functions were written in `services/database.py` and the IDE was correctly showing them (autocomplete, docstrings, go-to-definition all worked). Importing them in `app.py` raised an `ImportError` at runtime.

**Why it matters:**  
The IDE reads the in-memory buffer — it shows you what you've typed, whether or not it has been written to disk. The running Python process (and any tool that reads files from disk) sees only the saved version. Until you save, your changes don't exist outside the editor. When an `ImportError` says a name doesn't exist, check that the file is saved before looking for deeper causes.

---

### 14. Jupyter caches imported modules — restart the kernel after changing backing files

**The situation:**  
`llm_client.py` was edited to fix a bug in `llm_question_generator`. The notebook was re-run and the output was still wrong, even though the fix was correctly saved on disk.

**Why it matters:**  
When a Jupyter notebook runs `import services.llm_client`, Python loads the module into memory and caches it. If you edit the `.py` file afterwards, Jupyter keeps using the cached version — it does not detect or reload the change. The fix only takes effect after restarting the kernel (which clears the cache) and re-running all cells. This applies to any `.py` file imported by the notebook, not just `llm_client`.

**The rule:** Changed a `.py` file that a running notebook imports? Restart the kernel before re-running.

---

### 13. Leading spaces before `#` break Markdown headings

**The bug:**
```python
question_text += (f"\n\n ### Question {idx+1}: \n\n {question}\n\n")
```

The output rendered as plain text rather than a heading, producing a flat block instead of three separate sections.

**The fix:**
```python
question_text += (f"\n\n### Question {idx+1}:\n\n{question}\n\n")
```

**Why it matters:**  
Markdown heading syntax (`#`, `##`, `###`) only works when the `#` characters appear at the very start of the line. Any leading whitespace — even a single space — causes the parser to treat the line as plain text. This is easy to miss when building strings with f-strings, where indentation inside the string literal becomes part of the output.

---

### 15. Streamlit nested buttons don't work — use session state for confirmation flows

**The bug:**
```python
if st.button("Rebuild Database"):
    st.warning("Are you sure?")
    if st.button("Yes"):       # this button never fires
        rebuild_database()
```

**The fix:**
```python
if st.button("Rebuild Database"):
    st.session_state.confirm_rebuild = True

if st.session_state.confirm_rebuild:
    st.warning("Are you sure?")
    if st.button("Yes, rebuild it"):
        rebuild_database()
        st.session_state.confirm_rebuild = False
        st.rerun()
```

**Why it matters:**  
Every interaction in Streamlit triggers a full page rerun from top to bottom. When you click "Rebuild Database", the page reruns and renders the inner "Yes" button — but `st.button` returns `True` only on the *single rerun* caused by that click. On the next rerun (when the user clicks "Yes"), `st.button("Rebuild Database")` returns `False`, so the entire inner block never executes and the "Yes" click is silently ignored. The correct pattern is to set a session state flag when the first button is clicked, then render the confirmation UI based on that flag. Session state persists across reruns, so the confirmation prompt stays visible until explicitly cleared.

---

### 12. `=+` is not `+=` — operator typos produce silent wrong behaviour

**The bug:**
```python
log_entry_Date = datetime.date(2026, 4, 1)

for current_recording in recordings:
    process_log_entry(log_entry_Date, current_recording)
    log_entry_Date =+ 1   # intended +=, actually assigns unary +1
```

After the first iteration `log_entry_Date` silently became the integer `1`, so every subsequent log entry was written to the database with `entry_date = 1` instead of the next calendar date.

**The fix:**
```python
log_entry_Date += datetime.timedelta(days=1)
```

**Why it matters:**  
`=+` is valid Python — it means "assign the unary positive of the right-hand side", so `x =+ 1` is the same as `x = 1`. No error is raised, the loop keeps running, and the damage (corrupt database rows) only becomes visible later. When incrementing dates, always use `timedelta`; never use bare integer arithmetic on `date` objects.

---

## Session 3 — 2026-05-18

---

### 17. `shutil.copy2` raises WinError 32 when source and destination are the same file

**The situation:**  
`save_uploaded_audio()` uses `shutil.copy2(source, destination)` to move audio files into `RECORDINGS_DIR`. During a database rebuild, the source files are already in `RECORDINGS_DIR`, so the source and destination paths resolved to the same file. On Windows this raises a cryptic `[WinError 32] The process cannot access the file because it is being used by another process` — not the "same file" error you'd expect.

The existing guard only checked whether to *delete* the original after copying — it never prevented the copy itself from running:
```python
shutil.copy2(audio_file, DESTINATION_PATH)          # crashes if same file
if audio_file.startswith(str(RECORDINGS_DIR)):
    os.remove(audio_file)                           # delete guard, too late
```

**The fix:**
```python
if os.path.abspath(audio_file) == os.path.abspath(DESTINATION_PATH):
    return DESTINATION_PATH   # same file — nothing to do

shutil.copy2(audio_file, DESTINATION_PATH)
```

**Why it matters:**  
Two lessons here. First, Windows surfaces the "same file" copy error as a file-locking error (WinError 32), not a "same path" error — which sent debugging down the wrong track entirely. Print statements showing the source and destination paths are what revealed the real cause.

Second, always compare paths with `os.path.abspath()` rather than raw string equality. Paths can look different on the surface (`./recordings/file.wav` vs `C:\project\recordings\file.wav`) but resolve to the same location. String comparison would miss those cases; `abspath` normalises both before comparing.

---

### 16. Use a callback to report progress from a function without coupling it to the UI

**The situation:**  
`rebuild_database()` in `controller.py` loops through audio files and calls `process_log_entry()` for each one. The admin panel showed only a spinner — no indication of how far through the rebuild it was.

The naive fix would be to put Streamlit calls (`st.progress`, `st.write`) directly inside `rebuild_database()`. That works, but it ties a backend service function to a specific UI framework — the controller can no longer be called from a script, a test, or a different page without dragging Streamlit in with it.

**The fix — a progress callback:**
```python
# controller.py — accepts an optional function, knows nothing about Streamlit
def rebuild_database(on_progress=None):
    wav_files = [f for f in os.listdir(RECORDINGS_DIR) if f.endswith('.wav')]
    total = len(wav_files)

    for i, file in enumerate(wav_files):
        if on_progress:
            on_progress(i, total, file)   # call whatever was passed in
        process_log_entry(...)

    if on_progress:
        on_progress(total, total, "Done")

# admin_panel.py — owns the UI, passes a closure that updates it
progress_bar = st.progress(0, text="Starting rebuild...")
status = st.empty()

def on_progress(current, total, filename):
    pct = current / total
    progress_bar.progress(pct, text=f"Processing {current + 1} of {total}...")
    status.caption(f"Current file: `{filename}`")

rebuild_database(on_progress=on_progress)
```

**Why it matters:**  
This is the *callback pattern* — instead of doing the work itself, a function accepts another function as an argument and calls it at key points. The controller stays UI-agnostic: pass `None` and nothing happens; pass a logging function and it logs; pass a Streamlit closure and it updates the UI. The caller decides what "report progress" means.

Two Streamlit-specific details make the live update work:
- `st.progress(value, text=...)` renders a progress bar. Calling `.progress()` on the same object again *replaces* it in place rather than appending a new one — so the bar fills smoothly rather than stacking up.
- `st.empty()` reserves a single placeholder slot. Calling `.caption()` (or `.write()`, `.text()`, etc.) on it overwrites whatever was there before. Without `st.empty()`, each call would append a new line of text, flooding the page.

---

## Session 4 — 2026-07-19 (fixes from code review v2)

---

### 18. Valid YAML is not the same as valid configuration

**The bug (`docker-compose.yaml`):**
```yaml
depends_on:
  - db:                        # a LIST containing a mapping
    condition: service_healthy
```

**The fix:**
```yaml
depends_on:
  db:                          # a MAPPING keyed by service name
    condition: service_healthy
```

**Why it matters:**
The broken version parses perfectly well as YAML — it produces `[{db: None, condition: service_healthy}]`, a list with one dictionary in it. But Compose's *schema* only accepts `depends_on` in two shapes: a list of strings (`- db`, short form) or a mapping of service names (long form, required when you use `condition:`). A list of mappings matches neither, so `docker compose up` refuses to start the whole stack.

The lesson generalises: YAML/JSON files have two layers of validity — syntax (will it parse?) and schema (does the tool accept this shape?). An editor only checks the first. The mistake here was mixing the two forms: starting from the short list form (`- db`) and grafting the long form's `condition` onto it. When switching from short to long form, the leading `-` has to go.

Also caught here: the `db` service was commented "not currently being used" while `depends_on` made the app refuse to start without it. When a comment and the code disagree, one of them is lying — update whichever is wrong before a future reader trusts the wrong one.

---

### 19. Streamlit forbids nested expanders — and a page-wide `try/except` hid the crash

**The bug (`log_history.py`, `search_logs.py`):**
```python
with st.expander(entry_date):
    with st.expander("View log data"):      # StreamlitAPIException at render time
        with st.expander("Transcript"):
            ...
```

An `st.expander` may not contain another `st.expander` — Streamlit raises the moment the page renders with at least one entry. In `log_history.py` this was wrapped in a page-wide `try/except` that displayed the exception, so the page showed a red traceback instead of the history. In `search_logs.py` the first successful search crashed outright.

**The fix:** one expander per entry, with `st.tabs` inside it for the sections:
```python
with st.expander(entry_date):
    tab_log, tab_transcript, tab_audio = st.tabs(["Log", "Transcript", "Audio"])
    with tab_log: ...
    with tab_transcript: ...
```
Tabs (and columns, and containers) can nest inside expanders freely — only expander-in-expander is banned.

**Why it matters:**
Two lessons. The Streamlit one: check the docs for container nesting rules before building layout; the restriction is documented on `st.expander` itself.

The bigger one is about the `try/except` wrapper. Catching *every* exception at page level and rendering it converted a loud, immediate, impossible-to-miss development error into a page that "sort of renders" — which is exactly why the bug shipped. During development you want pages to fail loudly. If you catch at all, catch narrowly (a specific exception, around a specific operation), and let genuine bugs crash where you'll see them.

Note the widgets inside the loop now need explicit `key=` arguments (`key=f"transcript-{entry_date}"`). Streamlit identifies widgets by hashing their parameters; two widgets in a loop with identical parameters collide with a `DuplicateWidgetID` error. A unique key per iteration prevents that.

---

### 20. Do the existence check *before* the read — and keep the blast radius per-item

**The bug (`log_history.py`):**
```python
st.download_button(..., data=log_file.read_bytes(), ...)  # raises if the file is missing
...
if log_file.exists():                                     # checked AFTER the read
    st.markdown(log_file.read_text(...))
```

`read_bytes()` on a missing file raises `FileNotFoundError`. The `exists()` check was in the code — just below the line that needed it. Combined with the page-wide `try/except` (see #19), **one** database row whose markdown file had been deleted took down the entire history page for every other entry.

**The fix:** gate everything that touches the file behind the check:
```python
if log_file.exists():
    st.download_button(..., data=log_file.read_bytes(), ...)
    st.markdown(log_file.read_text(encoding="utf-8"))
else:
    st.caption("Markdown file not found for this entry.")
```

**Why it matters:**
Guards only protect the code that comes after them. When you add a new operation on a resource (here, the download button was added after the markdown rendering already existed), it has to go *inside* the existing guard, not before it.

The second principle: on a page that renders many independent items, one bad item should degrade to a per-item message ("file not found for this entry"), never kill the whole page. Structure the code so each iteration of the loop is self-contained in its failure handling.

---

### 21. Return shapes callers can guess wrong — the dict keyed by `enumerate()` index

**The bug (`database.py` → `admin_panel.py`):**
```python
# api_get_logs returned:
return {idx: row_to_dict(row) for idx, row in enumerate(results)}   # {0: {...}, 1: {...}}

# admin_panel.py assumed the keys were dates:
dates = sorted(headers.keys())
st.caption(f"Earliest entry: {dates[0]}")        # rendered "Earliest entry: 0"
st.selectbox("Select entry to manage", options=sorted(headers.keys(), ...))  # offered 14, 13, 12...
```

**The fix:** key the dict by the thing callers actually look things up by:
```python
return {row[1]: row_to_dict(row) for row in results}   # keyed by entry_date
```

**Why it matters:**
A dict keyed by `0, 1, 2...` carries no information — it's a list wearing a dict costume, and it invites exactly this bug: a caller sees a dict, assumes the keys mean something, and builds UI on that assumption. The function and the page were both written by the same person, weeks apart — the second sitting guessed wrong about what the first sitting built.

Rule of thumb: if the keys are just positions, return a `list`. If callers need lookup, key by the *natural* lookup value (here, the date). And if a return shape needs a comment to explain, that's the shape telling you it's wrong. (Longer term, this is what dataclasses / ORM model objects fix properly.)

---

### 22. A stub behind a working UI is worse than no feature at all

**The bug:**
```python
def api_delete_log_entry(log_id: int):
    pass
```
The admin panel called this, then showed `st.success("Entry deleted.")`, cleared the cache, and rerendered. Everything *looked* like it worked. Nothing was deleted.

**The fix (two parts):**

The database function now deletes children before the parent — the foreign keys on `log_segment.log_entry_id` and `log_enrichment.log_entry_id` mean the parent row can't go first:
```python
session.execute(text("DELETE FROM log_enrichment WHERE log_entry_id = :log_id"), ...)
session.execute(text("DELETE FROM log_segment   WHERE log_entry_id = :log_id"), ...)
session.execute(text("DELETE FROM log_entry     WHERE id = :log_id"), ...)
session.commit()
```

And a new `controller.delete_log_entry(entry_date)` orchestrates the full delete: DB rows plus the generated `.md` file. It lives in the controller because deleting *files* is not the database layer's business — the same layering rule as the progress callback (#16).

**Why it matters:**
When a stub is unavoidable, it must be *loud*: `raise NotImplementedError`, never `pass` or a plausible-looking return value. `pass` behind a confirmation dialog and a success toast is the worst combination — the user trusts the system and the data silently disagrees.

One deliberate decision to remember: the delete **keeps the audio recordings**. They're the irreplaceable source data, and `rebuild_database()` reprocesses every `.wav` in the recordings folder — so a "deleted" entry will come back on the next rebuild. That's the safe default (audio is unrecoverable; DB rows are regenerable), but it's a real trade-off, and it's now documented in the function rather than left for someone to discover.

---

### 23. SQLite is forgiving about types; Postgres is not

**The bug (`get_weekly_transcripts`):**
```python
# entry_date column is String(25); start_date/end_date are Python date objects
WHERE entry_date BETWEEN :start_dt AND :end_dt
```
On SQLite this worked. On Postgres, psycopg2 sends `date` objects as typed DATE parameters, and Postgres has no `varchar >= date` operator — the query raises `operator does not exist: character varying >= date`. The Weekly Review page broke silently on the day the backend switched.

**The fix (immediate):** bind strings, since the column stores strings:
```python
{"start_dt": start_date.isoformat(), "end_dt": end_date.isoformat()}
```
This is correct *because* ISO-8601 dates (`2026-07-19`) sort chronologically as strings — that property is the only reason string comparison works here.

**Why it matters:**
SQLite has "type affinity" — it stores what you give it and compares loosely, which hides type mismatches between your schema and your code. Postgres enforces types strictly. Any type sloppiness that SQLite tolerated becomes a runtime error after migration, and it only surfaces on the specific queries that hit it — which is why every page needed a manual test after the switch (this one didn't get it).

The *real* fix is making `entry_date` an actual `Date` column (with a unique constraint) via an Alembic migration — then date objects bind naturally and the type system works for you instead of against you. That's on the roadmap; this entry is the reminder of why it matters.

---

### 24. Build separated strings with `join()`, not by appending after the loop

**The bug (`get_unified_transcripts`):**
```python
for transcript in transcripts:
    transcripts_result += transcript[2]
transcripts_result += '\n\n'          # separator added ONCE, after the loop
```
Two recordings in one day produced `...end of first sentenceStart of second...` — the segments were glued together with no separator, and that mangled text then flowed into the LLM formatting prompt and the search index.

**The fix:**
```python
transcripts_result = '\n\n'.join(transcript[2] for transcript in transcripts)
```

**Why it matters:**
`'\n\n'.join(items)` puts the separator *between* items — exactly the intent — and handles the edge cases (one item: no separator; zero items: empty string) for free. Hand-rolled `+=` loops always get one of those edges wrong. Whenever you find yourself concatenating in a loop, reach for `join()`; it's also faster, since repeated `+=` on strings copies the accumulated string every iteration.

---

### 25. `delete=False` temp files are your responsibility — clean up in `finally`

**The bug (`record.py`, `tools.py`):**
```python
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    tmp.write(file.read())
    tmp_path = tmp.name
ctrl.process_log_entry(tmp_path, ...)   # tmp file never deleted afterwards
```
`delete=False` is needed because the file must be reopened by path after the `with` block (ffmpeg and the whisper upload read it by name). But nothing ever deleted it — every recording left a `.wav` in `/tmp`, and inside the Docker container those accumulate until the container is rebuilt.

**The fix:**
```python
tmp_path = None
try:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio.read())
        tmp_path = tmp.name
    ctrl.process_log_entry(tmp_path, ...)
finally:
    if tmp_path and os.path.exists(tmp_path):
        os.unlink(tmp_path)
```

**Why it matters:**
`finally` runs whether the processing succeeded or raised, so the file is removed in both cases. The `tmp_path = None` initialisation before the `try` matters too — if the temp file creation itself fails, the `finally` block still runs, and without the initialisation it would hit an unbound variable (the same trap as #5). Pattern to memorise: *resource created outside a context manager → cleanup in `finally`, with the variable pre-initialised to `None`.*

---

### 26. `cast()` changes nothing at runtime — it just silences the type checker

**The bug (`record.py`):**
```python
if live_recording:
    file = cast(UploadedFile, live_recording)
else:
    file = cast(UploadedFile, uploaded_file)   # uploaded_file can be None!
tmp.write(file.read())                          # AttributeError on None
```
Clicking "Process recording" with no recording and no upload crashed with `AttributeError: 'NoneType' object has no attribute 'read'`.

**The fix:**
```python
audio = live_recording or uploaded_file
if audio is None:
    st.error("Please record a voice message or upload a file first.")
    st.stop()
```

**Why it matters:**
`typing.cast(X, value)` is a *promise to the type checker*, not a conversion — at runtime it returns `value` completely unchanged. `cast(UploadedFile, None)` is still `None`. The type checker was originally complaining that `uploaded_file` might be `None`; the `cast` didn't fix that problem, it hid it, and the hidden problem fired at runtime exactly as predicted.

This is the recurring theme with `cast` / `# type: ignore` / `# pyright: ignore`: the checker's complaint is almost always a true statement about your code. Answer it with a real runtime check (narrowing), after which the checker is satisfied *because the code is actually safe*. `x or y` is the idiomatic "first truthy of these" — followed by one explicit `None` check covering both.

---

### 27. Every write invalidates some cache — find it and clear it

**The bug (`weekly_review.py`):**
```python
@st.cache_data
def load_weekly_reviews(): ...

if st.button("Generate this week's review"):
    summary = ctrl.weekly_review(start_date, end_date)   # writes a new review file
    st.markdown(summary)
# "Past Weekly Reviews" below still shows the cached (stale) list
```
A newly generated review didn't appear in the list until the server restarted.

**The fix:**
```python
summary = ctrl.weekly_review(start_date, end_date)
load_weekly_reviews.clear()   # targeted: clears only this function's cache
```

**Why it matters:**
`@st.cache_data` keys on the function's *arguments* — it has no idea the underlying files changed. The discipline: after any write (DB insert, file write), ask "which cached reads are now stale?" and clear them. Prefer the targeted `function.clear()` over the sledgehammer `st.cache_data.clear()` — clearing everything forces every page to reload all data, when only one loader was stale.

Also fixed here: selecting only one date in the range picker used to do nothing, silently — `st.date_input` with a range value returns a 1-tuple until both ends are picked, and the `len(date_range) == 2` check had no `else`. Now it warns. A guard that fails silently teaches the user the button is broken.

---

### 28. Network calls without timeouts hang forever

**The bug (`llm_client.py`):**
```python
api_response = requests.post(f'{LLM_ENDPOINT}/api/chat', json=payload)   # no timeout
```
If Ollama accepts the connection but stalls mid-generation (which local LLM servers under load genuinely do), this waits *forever* — and since Streamlit runs the page script synchronously, the whole app freezes with no error and no way to recover except restarting the container.

**The fix:**
```python
api_response = requests.post(f'{LLM_ENDPOINT}/api/chat', json=payload, timeout=600)
api_response.raise_for_status()
```

**Why it matters:**
`requests` has **no default timeout** — this is a famous footgun (httpx, by contrast, defaults to 5 seconds, which is why the *other* calls in this project were already safe). Every network call should state its patience explicitly: generous for an LLM generating text (600s), tight for a health check (2s). A timeout converts an invisible hang into a visible, handleable exception.

`raise_for_status()` was also missing: without it, an HTTP 404/500 from Ollama flowed into the JSON parsing and surfaced as a confusing parse error three lines later, instead of an honest `HTTPError` at the call site. Fail at the point of failure, with the real reason.

---

### 29. An `if/elif` chain with no `else` can leave a variable unbound — or better, use a dict

**The bug (`transcription_cleanup`):**
```python
if mode_choice == "Transcription Cleanup":
    system_prompt = cleanup_prompt
elif mode_choice == "Note Taking":
    system_prompt = note_taking_prompt

call_llm_api(prompt=prompt, system=system_prompt, ...)   # UnboundLocalError for any other value
```
The UI's selectbox happened to only offer those two strings, so it never fired — but the function was one renamed option label away from crashing (and the coupling between UI label strings and this chain is invisible).

**The fix:**
```python
prompts = {
    "Transcription Cleanup": cleanup_prompt,
    "Note Taking": note_taking_prompt,
}
if mode_choice not in prompts:
    raise ValueError(f"Unknown processing mode: {mode_choice}")
system_prompt = prompts[mode_choice]
```

**Why it matters:**
Same root cause as #5: Python binds variables at runtime, so a branch that doesn't run means a name that doesn't exist. Every `if/elif` chain that *assigns* needs an `else` — even if the `else` just raises.

The dict-dispatch version is better than adding an `else`, though: the mapping from mode name to prompt becomes *data* you can read at a glance, adding a mode is one line instead of two more branch lines, and the valid options are enumerable (the UI could even build its selectbox from `list(prompts)`, removing the string coupling entirely).

Bonus micro-fix in the same sweep (`search_logs.py`): `st.spinner("Searching...")` was called bare, which does nothing — `st.spinner` is a context manager and only shows while a `with` block runs: `with st.spinner("Searching..."): results = ...`.

---
