# Captain's Log — Project Roadmap

A phased build plan designed for spare-time development. Each phase produces something
working and useful on its own, so you're never mid-feature for weeks on end.

---

## Phase 1 — Foundation & Environment Setup
**Goal:** Get your development environment ready and understand the key tools before writing any application code.
**Estimated effort:** 2–3 sessions

### Tasks
- [X] Install Python 3.11+ and set up a virtual environment for the project
- [X] Install and explore **Ollama** — pull a small model (e.g. `llama3.2:3b`) and confirm you can chat with it via its local API
- [X] Install **Faster-Whisper** and run a test transcription on any audio file (even a phone recording)
- [X] Create your project folder structure:
  ```
  captains_log/
  ├── api/            # FastAPI app (built later)
  ├── services/       # Whisper, Ollama, storage logic
  ├── data/
  │   ├── audio/      # Raw audio files
  │   └── logs/       # Markdown output files
  ├── db/             # Database files / migrations
  └── cli/            # Early command-line scripts
  ```
- [X] Initialise a Git repository and make your first commit

### Exit Criteria
You can run a Python script that sends a prompt to Ollama and prints the response, and you can transcribe a local audio file with Faster-Whisper.

---

## Phase 2 — Database & Data Model
**Goal:** Define how all data will be stored before building anything that generates it.
**Estimated effort:** 1–2 sessions

### Tasks
- [X] Choose your database — **SQLite** is recommended to start (zero config, single file, easy to inspect)
- [X] Install **SQLAlchemy** (ORM) and **Alembic** (migrations) — both will feel familiar coming from C#/Entity Framework territory
- [X] Design and create your schema:

```sql
-- A day's log container
CREATE TABLE log_entry (
    id          INTEGER PRIMARY KEY,
    entry_date  DATE NOT NULL UNIQUE,
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL
);

-- Individual recordings within a day
CREATE TABLE log_segment (
    id              INTEGER PRIMARY KEY,
    log_entry_id    INTEGER NOT NULL REFERENCES log_entry(id),
    audio_filename  TEXT NOT NULL,
    duration_secs   REAL,
    raw_transcript  TEXT,
    created_at      DATETIME NOT NULL
);

-- LLM-generated content for each day
CREATE TABLE log_enrichment (
    id              INTEGER PRIMARY KEY,
    log_entry_id    INTEGER NOT NULL REFERENCES log_entry(id),
    formatted_md    TEXT,         -- cleaned & formatted markdown
    followup_qs     TEXT,         -- JSON array of follow-up questions
    weekly_summary  TEXT,         -- populated on weekly review
    generated_at    DATETIME NOT NULL
);
```

- [X] Write a small test script that inserts a dummy log entry and reads it back
- [X] Add `.gitignore` entries for the SQLite file and audio data folder

### Exit Criteria
Database schema exists, Alembic can run migrations, and you can read/write records via SQLAlchemy.

---

## Phase 3 — CLI Recording & Transcription
**Goal:** You can record your voice from the terminal, save the file, and get a transcript back. No web UI yet.
**Estimated effort:** 2–3 sessions

### Tasks
- [X] Install **sounddevice** and **soundfile** (Python audio recording libraries)
- [X] Write `cli/record.py` — a script that:
  - Starts recording when you press Enter
  - Stops recording when you press Enter again
  - Saves the `.wav` file to `data/audio/` with a timestamped filename
- [X] Write `services/transcriber.py` — wraps Faster-Whisper:
  - Accepts an audio file path
  - Returns the transcript as a string
- [X] Wire them together: recording finishes → transcription runs → transcript printed to console
- [X] Save the audio filename and raw transcript to the database via SQLAlchemy

### Tips
- Start with a hardcoded 30-second max recording to keep things simple
- Don't worry about audio quality settings yet — defaults are fine

### Exit Criteria
Run `python cli/record.py`, speak for 30 seconds, and see your words printed to the terminal and saved to the DB.

---

## Phase 4 — LLM Enrichment & Markdown Output
**Goal:** The raw transcript gets polished by the LLM and saved as a formatted Markdown file.
**Estimated effort:** 2–3 sessions

### Tasks
- [X] Write `services/llm_client.py` — a thin wrapper around Ollama's local HTTP API:
  - `def complete(prompt: str, system: str) -> str`
  - Handle timeouts and basic error cases
- [X] Write a **formatting prompt** that instructs the LLM to:
  - Remove speech-to-text artefacts ("um", "uh", false starts)
  - Fix punctuation and capitalisation
  - Preserve the speaker's voice and meaning
  - Output clean Markdown with a date heading
- [X] Write `services/formatter.py` that calls the LLM and returns formatted Markdown
- [X] Save the formatted Markdown to `data/logs/YYYY-MM-DD.md`
- [X] Update the database `log_enrichment` record with the formatted content
- [X] Update `cli/record.py` to run formatting automatically after transcription

### Tips
- Spend time iterating on your prompt — this is the highest-leverage work in this phase
- Log the raw LLM response to a file during development so you can tweak the prompt without re-recording

### Exit Criteria
After a CLI recording session, a readable, formatted `.md` file appears in `data/logs/`.

---

## Phase 5 — Supplemental Recordings
**Goal:** You can add additional recordings to an existing day's log rather than only creating one per day.
**Estimated effort:** 1–2 sessions

### Tasks
- [X] Update `cli/record.py` to check if a log entry already exists for today
  - If yes: create a new `log_segment` linked to today's entry (append mode)
  - If no: create a new `log_entry` and first `log_segment`
- [X] Update `services/formatter.py` to combine all of a day's transcripts before formatting
  - Concatenate segments in time order, then pass to LLM as one block
- [X] Re-generate and overwrite the day's Markdown file when a new segment is added
- [X] Test by making two recordings in the same day and checking the output file

### Exit Criteria
Two separate CLI recording sessions on the same day produce one coherent Markdown log file.

---

## Phase 6 — LLM Follow-Up Questions
**Goal:** After recording, the LLM reviews your entry (and recent history) and generates thoughtful follow-up questions — the most Star Trek part of the project.
**Estimated effort:** 2–3 sessions

### Tasks
- [X] Write a **follow-up prompt** that:
  - Receives today's transcript and the previous 2–3 days' transcripts as context
  - Asks the LLM to generate 3–5 follow-up questions
  - Instructs it to notice threads across days (ongoing problems, mentioned intentions, unresolved items)
  - Returns output as a JSON array of question strings
- [X] Write `services/questioner.py` that calls the LLM and parses the JSON response
- [X] Store the questions in the `log_enrichment.followup_qs` column
- [X] Display questions in the terminal after a recording session
- [X] Append the questions as a section at the bottom of the day's Markdown file

### Tips
- Prompt engineering matters a lot here. A good starting instruction: *"You are a thoughtful captain's counsellor. Review the logs and ask questions that help the captain reflect, not just report."*
- Use `json.loads()` to parse the response — if the LLM returns malformed JSON, add a retry with a stricter prompt

### Exit Criteria
After recording, 3–5 contextual follow-up questions appear in the terminal and in the Markdown file.

---

## Phase 6b — SQLAlchemy ORM Refactor
**Goal:** Replace every raw `text()` SQL string in `services/database.py` with proper SQLAlchemy ORM operations that use the model classes defined in `services/models.py`. The models exist — now the rest of the code should actually use them.
**Estimated effort:** 1–2 sessions

### Tasks
- [ ] Refactor `create_or_get_log_header()` — replace the `SELECT` and `INSERT` raw strings with a `select(log_entry).where(...)` query and a `session.add(log_entry(...))` insert; return the model object instead of a bare `int`
- [ ] Refactor `create_log_segment()` — replace the raw `INSERT` with `session.add(log_segment(...))`, and replace the `GROUP_CONCAT` raw query by loading all segments via the `log_entry.log_segments` relationship and joining transcripts in Python
- [ ] Refactor `create_log_enrichment()` — replace the raw `INSERT` with `session.add(log_enrichment(...))`
- [ ] Refactor `reset_db()` — replace raw `DELETE` strings with ORM delete calls (`session.query(Model).delete()` or `delete(Model)` in 2.0 style)
- [ ] Verify `cli/end-to-end.ipynb` and `cli/recording_test.ipynb` still run correctly after the refactor

### Tips
- SQLAlchemy 2.0 style uses `select()` + `session.scalar()` / `session.scalars()` rather than the older `session.query()` — prefer the 2.0 style since that's what `models.py` uses (`Mapped`, `mapped_column`)
- After `session.add(new_object)` call `session.flush()` (before `session.commit()`) to populate the auto-generated `id` without closing the transaction — useful if you need the new ID immediately
- For the transcript aggregation, loading `entry.log_segments` and doing `" ".join(s.raw_transcript for s in entry.log_segments)` in Python is cleaner than a raw `GROUP_CONCAT` and avoids mixing ORM and raw SQL in the same function
- Once `database.py` is fully ORM-based, downstream callers (notebooks, future API routes) can receive model objects and access fields by attribute rather than by index, which is much easier to read

### Exit Criteria
`services/database.py` contains no `text(...)` calls. All reads and writes go through model class instances, and the end-to-end notebook still produces a correctly formatted log file.

---

## Phase 7 — Streamlit UI
**Goal:** Build a simple Streamlit app that puts a browser face on everything built so far — record audio, run the full pipeline, and browse your log history — with no HTML, JavaScript, or separate API layer required.
**Estimated effort:** 2–3 sessions

### Tasks
- [ ] Install Streamlit and a browser audio component: `pip install streamlit streamlit-audiorecorder`
- [X] Create `app.py` at the project root and confirm it runs with `streamlit run app.py`
- [ ] Build a **Record & Process** page:
  - Accept audio via `streamlit-audiorecorder` (browser mic) or `st.file_uploader` (upload a `.wav`/`.m4a` from disk)
  - Wire the audio through `services/transcriber.py` → `services/llm_client.py` → `services/database.py`
  - Display the transcript, formatted Markdown (`st.markdown()`), and follow-up questions once processing completes
- [X] Build a **Today's Log** view:
  - Load and render today's `data/logs/YYYY-MM-DD.md` on page load
  - Show follow-up questions below the entry
- [X] Build a **Log History** page:
  - Query the database for all log entries, newest first
  - Clicking an entry renders its Markdown and questions

- [ ] Refactor `app.py` into a multi-page structure — move each view into its own file under a `pages/` folder:
  - `pages/1_Record.py` — Record & Process page
  - `pages/2_Today.py` — Today's Log view
  - `pages/3_History.py` — Log History page
  - `pages/4_Weekly_Review.py` — Weekly Review page (currently in app.py)
  - Keep `app.py` as a thin entry point (title, sidebar config, shared state setup only)

### Tips
- Streamlit reruns the entire script on every interaction — use `st.session_state` to hold in-progress values (e.g. the transcript while the LLM is still formatting)
- Wrap slow operations in `st.spinner("Transcribing…")` and `st.spinner("Asking the LLM…")` so the UI doesn't look frozen
- Use Streamlit's multi-page app feature — put each page as a file inside a `pages/` folder and Streamlit generates the sidebar navigation automatically
- `st.audio(audio_bytes)` plays back any recording inline with no extra work
- For browser recording, `streamlit-audiorecorder` is the simplest drop-in; `st.file_uploader(type=["wav","m4a","mp3"])` is a good fallback for uploading phone recordings

### Exit Criteria
Open `http://localhost:8501`, record or upload audio, and see the formatted log and follow-up questions rendered in the browser.

---

## Phase 8 — Weekly Review
**Goal:** The system generates a weekly summary of all logs on demand from within the Streamlit UI.
**Estimated effort:** 2 sessions

### Tasks
- [X] Write a **weekly review prompt** that instructs the LLM to:
  - Summarise what was worked on across the week
  - Identify recurring themes or blockers
  - List any outstanding actions mentioned but not resolved
  - Note what went well vs. what didn't
- [X] Write `services/weekly_reviewer.py` (Added to the llm file instead)
- [ ] Save the summary to `data/logs/week-YYYY-WW.md` and to the database
- [X] Add a **Weekly Review** page to the Streamlit app with a "Generate this week's review" button that calls the LLM and renders the result with `st.markdown()`
- [ ] (Optional) Use **APScheduler** to trigger the review automatically every Sunday evening

### Exit Criteria
Clicking the button in the Streamlit app generates and displays a weekly summary Markdown document.

---

## Phase 9 — Polish & Quality of Life
**Goal:** Tighten up the rough edges before calling it v1.0.
**Estimated effort:** Ongoing

### Tasks
- [ ] Add audio playback to any log entry — `st.audio()` renders a player inline with no extra libraries
- [ ] Add a search page in Streamlit to search across all transcripts by keyword
- [ ] Improve error feedback in the UI (recording failures, LLM timeouts, missing audio device)
- [ ] Add a settings page to change the Ollama model, number of context days for follow-ups, etc. — store in a simple config file or `st.session_state`
- [ ] Write a `README.md` with setup instructions (you'll thank yourself later)
- [ ] Consider audio file compression to manage storage over time (FFmpeg + Python subprocess)
- [ ] Add log export — zip of all Markdown files available as a download via `st.download_button()`

---

## Future Phases (TBD) — REST API & Custom Web Frontend

These phases are deferred in favour of the Streamlit-first approach. The content is preserved here for reference if the project later needs a dedicated API layer, a mobile client, or a custom web interface.

---

### FastAPI Backend (TBD)
**Goal:** Wrap all services behind a proper HTTP API so any client (mobile app, custom web UI, CLI) can interact with them.

> **Note:** A scaffold (`api/main.py`) was started during Phase 7 before the switch to Streamlit. A health check endpoint and a partial `/logs` listing were implemented. This work has been removed from the repo for now but can be resumed from the TBD section below when needed.

#### Tasks
- [X] Install **FastAPI** and **Uvicorn**: `pip install fastapi uvicorn`
- [ ] Create `api/main.py` with the following endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/logs/segments` | Upload an audio file, trigger transcription + enrichment |
| `GET` | `/logs` | List all log entries (date, segment count) |
| `GET` | `/logs/{date}` | Get a specific day's full entry (transcripts, markdown, questions) |
| `GET` | `/logs/{date}/markdown` | Return the raw Markdown file |
| `GET` | `/logs/week` | Get this week's entries for weekly review |
| `POST` | `/logs/weekly-review` | Trigger a weekly summary for the current or specified week |

- [ ] Test all endpoints via the built-in Swagger UI at `http://localhost:8000/docs`
- [ ] Add basic error handling (404s, failed transcriptions, LLM timeouts)
- [ ] Install `python-multipart` for file upload support: `pip install python-multipart`

#### Tips
- FastAPI type hints and decorators will feel familiar — very similar mental model to ASP.NET minimal APIs in C#
- Run with: `uvicorn api.main:app --reload`

---

### Custom Web Frontend (TBD)
**Goal:** A purpose-built browser UI decoupled from the Python backend, communicating via the FastAPI layer above.

#### Tasks
- [ ] Serve static files from FastAPI (`StaticFiles` mount) or deploy separately
- [ ] Build `index.html` with a Record page, Today's Log view, and Log History list
- [ ] Use **HTMX** (single `<script>` tag, no npm) for reactive updates without a JS framework
- [ ] Use **`marked.js`** (single `<script>` tag) to render Markdown in the browser
- [ ] Handle recording state (idle → recording → processing → done) with the browser `MediaRecorder` API
- [ ] Style with a dark theme and monospace font for the aesthetic

---

## Dependency Summary

| Library | Purpose | Install |
|---------|---------|---------|
| `faster-whisper` | Local transcription | `pip install faster-whisper` |
| `sqlalchemy` | ORM | `pip install sqlalchemy` |
| `alembic` | DB migrations | `pip install alembic` |
| `sounddevice` | CLI audio recording | `pip install sounddevice` |
| `soundfile` | Audio file I/O | `pip install soundfile` |
| `streamlit` | Web UI framework | `pip install streamlit` |
| `streamlit-audiorecorder` | Browser mic recording | `pip install streamlit-audiorecorder` |
| `httpx` | HTTP client for Ollama | `pip install httpx` |
| Ollama | Local LLM server | https://ollama.com |
| **TBD** | | |
| `fastapi` | REST API framework (future) | `pip install fastapi` |
| `uvicorn` | ASGI server (future) | `pip install uvicorn` |
| `python-multipart` | File uploads in FastAPI (future) | `pip install python-multipart` |
| HTMX | Custom frontend interactivity (future) | CDN script tag |
| marked.js | Markdown rendering in browser (future) | CDN script tag |

---

## Rough Timeline

| Phase | Effort | Cumulative |
|-------|--------|-----------|
| 1. Environment Setup | 2–3 sessions | 2–3 |
| 2. Data Model | 1–2 sessions | 3–5 |
| 3. CLI Recording | 2–3 sessions | 5–8 |
| 4. LLM Enrichment | 2–3 sessions | 7–11 |
| 5. Supplemental Recordings | 1–2 sessions | 8–13 |
| 6. Follow-Up Questions | 2–3 sessions | 10–16 |
| 6b. SQLAlchemy ORM Refactor | 1–2 sessions | 11–18 |
| 7. Streamlit UI | 2–3 sessions | 13–21 |
| 8. Weekly Review | 2 sessions | 15–23 |
| 9. Polish | Ongoing | — |
| TBD. REST API & Custom Frontend | TBD | — |

At 1–2 sessions per week, you're looking at a fully working v1 in **3–5 months** with plenty of natural pause points along the way.

# Future ideas:

|Index|Idea|Details|
|-----|----|-------|
|1|Connect to the app from work laptop| This will require working out some networking issues|
|2|Phone App| Big wall to climb here as thats building a whole new thing|
|3|Multiple Journal Types| Allows you to break out work and personal entries|
|4|Larger review windows| Have monthly/quarterly/annual reviews|
|5|Vector Database to assist with reviews| As it says so the AI can get additional context when doing reviews|
|6|AI Tool Suite| AS I used the LLM more it might be useful to give the LLM tools to get additional data|
|7|Use larger models| As it says and compare results|
|8|A Project diary| Kind of a continuation of #3 but having a project that the LLM can mainly keep track of tasks.|