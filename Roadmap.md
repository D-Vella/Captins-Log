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
- [X] Install Streamlit and a browser audio component: `pip install streamlit streamlit-audiorecorder`
- [X] Create `app.py` at the project root and confirm it runs with `streamlit run app.py`
- [X] Build a **Record & Process** page:
  - Accept audio via `streamlit-audiorecorder` (browser mic) or `st.file_uploader` (upload a `.wav`/`.m4a` from disk)
  - Wire the audio through `services/transcriber.py` → `services/llm_client.py` → `services/database.py`
  - Display the transcript, formatted Markdown (`st.markdown()`), and follow-up questions once processing completes
- [X] Build a **Today's Log** view:
  - Load and render today's `data/logs/YYYY-MM-DD.md` on page load
  - Show follow-up questions below the entry
- [X] Build a **Log History** page:
  - Query the database for all log entries, newest first
  - Clicking an entry renders its Markdown and questions

- [X] Refactor `app.py` into a multi-page structure — move each view into its own file under a `pages/` folder:
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
- [X] Save the summary to `data/logs/week-YYYY-WW.md`
- [ ] Add the weekly review to the database.
- [X] Add a **Weekly Review** page to the Streamlit app with a "Generate this week's review" button that calls the LLM and renders the result with `st.markdown()`
- [X] Add a section in the above page to see previously generated reviews.
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
- [X] Add a transcription feature so you can use these features elsewhere.

---


# Captain's Log — Dockerisation Roadmap

> A phased plan to move Captain's Log from a locally-run developer setup into a containerised
> application that runs continuously on a home mini PC, accessible from any device on the home network.
> Designed for spare-time development — each phase leaves the application in a working state.

---

## Background & Goal

Currently the application runs by manually launching it from a terminal on a gaming PC. The goal
is to deploy it as a Docker stack on a Lenovo ThinkCentre M900 (32GB RAM) running Docker Desktop,
so that it is always on, always accessible via a browser on the home network, and backed up
via NAS volumes. Ollama will run as a sidecar container in the same stack, with the gaming PC's
Ollama instance available as a fallback if needed.

---

## Phase D1 — Verify Ollama on the Mini PC
**Goal:** Confirm the mini PC can run Ollama at an acceptable speed before committing to the architecture.
**Estimated effort:** 1 session

### Background
The mini PC has an integrated GPU only — Ollama will run entirely on CPU. This phase answers
the question "is it fast enough?" before any Docker work begins. There is no point containerising
an LLM that is too slow to be useful.

### Tasks
- [X] Install Ollama directly on the mini PC (not in Docker yet — just the native installer)
- [X] Pull the model: `ollama pull gemma4:e4b`
- [X] Run a timed test prompt and record how long it takes:
  ```bash
  ollama run gemma4:e4b "Summarise this in one sentence: Had a productive day working on the NAS setup."
  ```
- [X] Test a longer prompt — paste a full transcript and ask for markdown formatting
- [X] Record the response times in the Field Notes below
- [X] Decide: is the speed acceptable for a journaling tool where waiting 30-60 seconds is fine?

### Exit Criteria
You have a real response time for a realistic prompt on the mini PC hardware and a clear decision
on whether to run Ollama there or keep it on the gaming PC as primary.

---

## Phase D2 — Ollama Fallback in llm_client.py
**Goal:** Update the LLM client to try the gaming PC's Ollama first and fall back to a second
instance if unreachable. This keeps the app working whether or not the gaming PC is on.
**Estimated effort:** 1 session

### Background
The app currently has a hardcoded Ollama endpoint. This phase introduces a simple health check
so the app can decide at runtime which Ollama instance to use. This is done in Python before
any Docker work — it can be tested on your existing setup by temporarily pointing primary at
a bad address to force the fallback.

### Tasks
- [X] Add two Ollama endpoint values to `services/config.py`:
  ```python
  OLLAMA_PRIMARY = "http://192.168.x.x:11434"   # gaming PC — update with real IP
  OLLAMA_FALLBACK = "http://ollama:11434"         # docker sidecar service name
  ```
- [X] Write a `get_ollama_endpoint()` function in `services/llm_client.py`:
  ```python
  def get_ollama_endpoint() -> str:
      try:
          httpx.get(f"{OLLAMA_PRIMARY}/api/tags", timeout=2)
          return OLLAMA_PRIMARY
      except Exception:
          return OLLAMA_FALLBACK
  ```
- [X] Update all Ollama calls in `llm_client.py` to use `get_ollama_endpoint()` rather than a hardcoded URL
- [X] Test the fallback by temporarily changing `OLLAMA_PRIMARY` to a bad address and confirming the app still works
- [X] Restore the correct primary address and commit

### Exit Criteria
The app selects the correct Ollama endpoint automatically. Pointing primary at a bad address causes
a clean fallback with no crash. The gaming PC address is not hardcoded anywhere in the codebase.

---

## Phase D3 — Prepare the App for Docker
**Goal:** Make the application ready to run inside a container by resolving assumptions that only
work on a local developer machine.
**Estimated effort:** 1–2 sessions

### Background
Docker containers are isolated environments. Things that work on your machine — relative file paths,
hardcoded drive letters, environment-specific config — will break inside a container unless you
address them first. This phase is about making the app portable before containerising it.

### Tasks
- [X] Audit `services/config.py` for any Windows-specific paths (drive letters, backslashes)
  — replace with `pathlib.Path` relative paths if not already done
- [X] Ensure `data/recordings/` and `data/logs/` are created by `ensure_directories()` at startup
  — these will be mounted as Docker volumes
- [X] Move any remaining hardcoded configuration values into environment variables using `python-dotenv`:
  ```python
  # .env
  OLLAMA_PRIMARY=http://192.168.x.x:11434
  OLLAMA_FALLBACK=http://ollama:11434
  ```
- [X] Add `python-dotenv` loading to `services/config.py` if not already present
- [X] Generate a clean `requirements.txt` from your virtual environment:
  ```bash
  pip freeze > requirements.txt
  ```
- [X] Review `requirements.txt` and remove anything that is clearly a dev-only tool
  (e.g. `ipykernel`, `nbstripout`) — these do not belong in a production container
- [X] Confirm the app runs cleanly from a fresh terminal with no VS Code involvement

### Exit Criteria
The app starts and runs using only environment variables for configuration. No hardcoded paths
or Windows-specific assumptions remain. `requirements.txt` is clean and accurate.

---

## Phase D4 — Write the Dockerfile
**Goal:** Write a Dockerfile that builds a container image for the Captain's Log Streamlit app.
**Estimated effort:** 1 session

### Background
A Dockerfile is a set of instructions for building a container image — think of it like a recipe
that starts from a base OS, installs your dependencies, copies your code, and defines how to
start the app. You write it once and Docker uses it to produce a repeatable, portable image.

### Tasks
- [X] Create `Dockerfile` in the project root:
  ```dockerfile
  FROM python:3.12-slim

  WORKDIR /app

  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  COPY . .

  EXPOSE 8501

  CMD ["streamlit", "run", "app.py", \
       "--server.address", "0.0.0.0", \
       "--server.sslCertFile", "cert.pem", \
       "--server.sslKeyFile", "key.pem"]
  ```
- [X] Add a `.dockerignore` file to prevent unnecessary files being copied into the image:
  ```
  .git
  .env
  __pycache__
  *.pyc
  data/
  db/
  notebooks/
  *.pem
  ```
- [X] Build the image locally on your gaming PC to confirm it builds without errors:
  ```bash
  docker build -t captains-log .
  ```
- [X] Fix any build errors before moving on — do not proceed to Compose until the image builds cleanly

### Tips
- `python:3.12-slim` is a minimal Python image — smaller and faster to build than the full version
- The `--no-cache-dir` flag on pip keeps the image size down
- Data and database files are excluded from the image because they will be mounted as volumes

### Exit Criteria
`docker build` completes without errors. The image exists locally. No sensitive files or data
directories are baked into the image.

---

## Phase D5 — Docker Compose Stack
**Goal:** Write a Docker Compose file that runs the app and Ollama together as a single stack,
with volumes for persistent data.
**Estimated effort:** 1–2 sessions

### Background
Docker Compose lets you define multiple containers that work together as a single application.
In your case the stack has two services: the Captain's Log app and an Ollama instance.
Containers in the same Compose stack communicate by service name — so the app reaches Ollama
at `http://ollama:11434` without any IP addresses or port configuration between them.

Volumes are how data persists beyond the container's lifetime. Without them, everything inside
a container is lost when it stops. By mounting your `data/` and `db/` folders as volumes pointing
to your NAS or a local folder on the mini PC, your logs and database survive restarts.

### Tasks
- [X] Create `docker-compose.yml` in the project root:
  ```yaml
  services:
    app:
      build: .
      ports:
        - "8501:8501"
      depends_on:
        - ollama
      env_file:
        - .env
      volumes:
        - ./data:/app/data
        - ./db:/app/db
        - ./cert.pem:/app/cert.pem:ro
        - ./key.pem:/app/key.pem:ro
      restart: unless-stopped

    ollama:
      image: ollama/ollama
      volumes:
        - ollama_models:/root/.ollama
      restart: unless-stopped

  volumes:
    ollama_models:
  ```
- [ ] Create a `.env` file on the mini PC (not committed to Git) with the correct values
- [ ] Copy the SSL certificate files (`cert.pem`, `key.pem`) to the mini PC
- [ ] Start the stack: `docker compose up -d`
- [ ] Pull the model into the Ollama container:
  ```bash
  docker exec -it captains-log-ollama-1 ollama pull gemma4:e4b
  ```
- [ ] Open a browser and confirm the app is accessible at `https://[mini-pc-ip]:8501`
- [ ] Make a test log entry end to end and confirm it saves correctly

### Tips
- `restart: unless-stopped` means Docker restarts the containers automatically after a reboot
- The `ollama_models` named volume persists the downloaded model — it will not need re-downloading
  every time the stack restarts
- `docker compose logs -f app` streams the app logs live if you need to debug

### Exit Criteria
The full stack starts with one command. A test log entry completes end to end. Data persists
after a `docker compose down` and `docker compose up` cycle.

---

## Phase D6 — NAS Volume Integration
**Goal:** Point the data and database volumes at a location on the NAS so that all log data
is backed up automatically.
**Estimated effort:** 1 session

### Background
Currently the volumes point to local folders on the mini PC's SSD. This phase moves them to
a NAS mount so the data is backed up alongside everything else on the NAS. The mini PC SSD
is a 240GB drive shared with Docker and the OS — not the right long-term home for log data.

### Tasks
- [X] Confirm the NAS share is mounted on the mini PC and accessible as a path
- [ ] Create the target directories on the NAS:
  ```
  /mnt/nas/captains-log/data/
  /mnt/nas/captains-log/db/
  ```
- [ ] Update `docker-compose.yml` to point volumes at the NAS mount:
  ```yaml
  volumes:
    - /mnt/nas/captains-log/data:/app/data
    - /mnt/nas/captains-log/db:/app/db
  ```
- [ ] Restart the stack and confirm the app still works
- [ ] Verify that a new log entry creates files on the NAS, not the local SSD
- [ ] Confirm NAS backups include these directories

### Exit Criteria
Log files and the database are written to the NAS. The mini PC SSD contains no application data.
A test log entry is visible in the NAS directory.

---

## Phase D7 — Portainer Integration & Ongoing Management
**Goal:** Manage the Captain's Log stack through Portainer rather than the command line.
**Estimated effort:** 1 session

### Tasks
- [ ] Add the Captain's Log stack to Portainer via the Compose file
- [ ] Confirm you can start, stop, and restart the stack from the Portainer UI
- [ ] Set up a simple update process for when the app code changes:
  ```bash
  docker compose build --no-cache
  docker compose up -d
  ```
- [ ] Document the update process in `README.md` so you don't have to remember it
- [ ] Confirm Portainer shows container health and logs for both services

### Exit Criteria
The stack is visible and manageable in Portainer. You can restart it without touching the command line.
The update process is documented.

---

## Dependencies Reference

| Tool | Purpose |
|------|---------|
| Docker Desktop | Container runtime on mini PC |
| Portainer | Docker management UI |
| `python-dotenv` | Environment variable loading |
| `ollama/ollama` | Official Ollama Docker image |

---

## Field Notes
*Use this section as a running log of discoveries, decisions, and gotchas encountered during the Dockerisation work.*

- [Date] — Ollama CPU-only response time on mini PC: [record actual times here]
- [Date] — Decision on primary/fallback Ollama: [record outcome here]
- [Date] — NAS mount path on mini PC: [record actual path here]



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