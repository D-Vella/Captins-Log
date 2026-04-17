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
- [ ] Install **SQLAlchemy** (ORM) and **Alembic** (migrations) — both will feel familiar coming from C#/Entity Framework territory
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
- [ ] Install **sounddevice** and **soundfile** (Python audio recording libraries)
- [ ] Write `cli/record.py` — a script that:
  - Starts recording when you press Enter
  - Stops recording when you press Enter again
  - Saves the `.wav` file to `data/audio/` with a timestamped filename
- [X] Write `services/transcriber.py` — wraps Faster-Whisper:
  - Accepts an audio file path
  - Returns the transcript as a string
- [ ] Wire them together: recording finishes → transcription runs → transcript printed to console
- [ ] Save the audio filename and raw transcript to the database via SQLAlchemy

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
- [ ] Update `cli/record.py` to run formatting automatically after transcription

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
- [ ] Update `cli/record.py` to check if a log entry already exists for today
  - If yes: create a new `log_segment` linked to today's entry (append mode)
  - If no: create a new `log_entry` and first `log_segment`
- [ ] Update `services/formatter.py` to combine all of a day's transcripts before formatting
  - Concatenate segments in time order, then pass to LLM as one block
- [ ] Re-generate and overwrite the day's Markdown file when a new segment is added
- [ ] Test by making two recordings in the same day and checking the output file

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
- [ ] Append the questions as a section at the bottom of the day's Markdown file

### Tips
- Prompt engineering matters a lot here. A good starting instruction: *"You are a thoughtful captain's counsellor. Review the logs and ask questions that help the captain reflect, not just report."*
- Use `json.loads()` to parse the response — if the LLM returns malformed JSON, add a retry with a stricter prompt

### Exit Criteria
After recording, 3–5 contextual follow-up questions appear in the terminal and in the Markdown file.

---

## Phase 7 — FastAPI Backend
**Goal:** Wrap all your CLI services behind a proper HTTP API so a browser can interact with them.
**Estimated effort:** 3–4 sessions

### Tasks
- [ ] Install **FastAPI** and **Uvicorn**
- [ ] Create `api/main.py` with the following endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/logs/segments` | Upload an audio file, trigger transcription + enrichment |
| `GET` | `/logs` | List all log entries (date, segment count) |
| `GET` | `/logs/{date}` | Get a specific day's full entry (transcripts, markdown, questions) |
| `GET` | `/logs/{date}/markdown` | Return the raw Markdown file |
| `GET` | `/logs/week` | Get this week's entries for weekly review |

- [ ] Move your service logic from the CLI scripts into the `services/` layer (most of it probably already is)
- [ ] Test all endpoints using **FastAPI's built-in Swagger UI** at `http://localhost:8000/docs` — no frontend needed yet
- [ ] Add basic error handling (404s, failed transcriptions, LLM timeouts)

### Tips
- FastAPI will feel very comfortable — type hints, decorators, and clear structure. Very similar mental model to ASP.NET minimal APIs in C#.
- Run with: `uvicorn api.main:app --reload`

### Exit Criteria
All endpoints work via the Swagger UI. You can upload an audio file via the browser and get a transcript back.

---

## Phase 8 — Web Frontend (Basic)
**Goal:** A simple browser UI that lets you record, view logs, and see follow-up questions. No frameworks — just HTML and HTMX.
**Estimated effort:** 3–5 sessions

### Tasks
- [ ] Install **HTMX** (just a `<script>` tag — no npm needed)
- [ ] Serve static files from FastAPI (`StaticFiles` mount)
- [ ] Build `index.html` with three sections:
  - **Record** — a button that uses the browser's `MediaRecorder` API to record and POST the audio to `/logs/segments`
  - **Today's Log** — loads and displays today's formatted Markdown and follow-up questions
  - **Log History** — a simple list of past entries with links
- [ ] Style it simply — aim for functional, not beautiful, at this stage. Dark theme + monospace font goes a long way for the aesthetic.
- [ ] Handle the recording state (idle → recording → processing → done) with basic JS

### Tips
- `MediaRecorder` in the browser records to a `Blob`, which you send as `multipart/form-data` to FastAPI
- HTMX lets you reload the "Today's Log" panel automatically after a recording completes — no page refresh needed
- Look up the **`marked.js`** library (one script tag) to render Markdown in the browser

### Exit Criteria
You can open a browser, record your voice, and see the formatted log and follow-up questions appear on screen — end-to-end in the UI.

---

## Phase 9 — Weekly Review
**Goal:** The system automatically (or on demand) generates a weekly summary of all logs.
**Estimated effort:** 2 sessions

### Tasks
- [ ] Write a **weekly review prompt** that instructs the LLM to:
  - Summarise what was worked on across the week
  - Identify recurring themes or blockers
  - List any outstanding actions mentioned but not resolved
  - Note what went well vs. what didn't
- [ ] Write `services/weekly_reviewer.py`
- [ ] Add a `/logs/weekly-review` POST endpoint that triggers the review for the current or specified week
- [ ] Save the summary to `data/logs/week-YYYY-WW.md` and to the database
- [ ] Add a "Generate Weekly Review" button to the UI
- [ ] (Optional) Use **APScheduler** to run this automatically every Sunday evening

### Exit Criteria
Clicking a button in the browser generates and displays a weekly summary Markdown document.

---

## Phase 10 — Polish & Quality of Life
**Goal:** Tighten up the rough edges before calling it v1.0.
**Estimated effort:** Ongoing

### Tasks
- [ ] Add audio playback to the UI — let you listen back to any segment
- [ ] Add a search endpoint and UI to search across all transcripts by keyword
- [ ] Improve error feedback in the UI (recording failures, LLM timeouts)
- [ ] Add a simple settings page to change the Ollama model, number of context days for follow-ups, etc.
- [ ] Write a `README.md` with setup instructions (you'll thank yourself later)
- [ ] Consider audio file compression to manage storage over time (FFmpeg + Python subprocess)
- [ ] Add log export — zip of all Markdown files for backup

---

## Dependency Summary

| Library | Purpose | Install |
|---------|---------|---------|
| `faster-whisper` | Local transcription | `pip install faster-whisper` |
| `sqlalchemy` | ORM | `pip install sqlalchemy` |
| `alembic` | DB migrations | `pip install alembic` |
| `fastapi` | Web API framework | `pip install fastapi` |
| `uvicorn` | ASGI server | `pip install uvicorn` |
| `sounddevice` | CLI audio recording | `pip install sounddevice` |
| `soundfile` | Audio file I/O | `pip install soundfile` |
| `httpx` | HTTP client for Ollama | `pip install httpx` |
| `python-multipart` | File uploads in FastAPI | `pip install python-multipart` |
| Ollama | Local LLM server | https://ollama.com |
| HTMX | Frontend interactivity | CDN script tag |
| marked.js | Markdown rendering | CDN script tag |

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
| 7. FastAPI Backend | 3–4 sessions | 13–20 |
| 8. Web Frontend | 3–5 sessions | 16–25 |
| 9. Weekly Review | 2 sessions | 18–27 |
| 10. Polish | Ongoing | — |

At 1–2 sessions per week, you're looking at a fully working v1 in **3–5 months** with plenty of natural pause points along the way.