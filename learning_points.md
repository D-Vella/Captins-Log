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
