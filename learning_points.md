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
