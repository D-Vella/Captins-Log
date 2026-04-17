# Captain's Log — Outstanding Tasks (Phases 1–6)

Outstanding items from the roadmap that haven't been completed yet.

---

## Phase 2 — Database & Data Model

- [ ] **Install SQLAlchemy and Alembic**

  The project currently uses raw `sqlite3` directly. The roadmap calls for SQLAlchemy (ORM) and Alembic (migrations) to manage the schema in a more maintainable way.

  **Tips:**
  - `pip install sqlalchemy alembic`
  - Run `alembic init alembic` from the project root to create the migrations folder
  - Convert `services/database.py` to use SQLAlchemy `Session` and mapped models instead of raw `cursor.execute()` calls
  - Once SQLAlchemy models exist, run `alembic revision --autogenerate -m "initial schema"` to generate your first migration
  - Note: if you prefer to stay with raw SQLite3 long-term, update the roadmap to reflect that decision rather than leaving this as a false open item

---

## Phase 3 — CLI Recording & Transcription

- [ ] **Install sounddevice and soundfile**

  These are the Python libraries used to capture audio from your microphone and write `.wav` files.

  **Tips:**
  - `pip install sounddevice soundfile`
  - On Linux you may also need `sudo apt install libportaudio2`
  - Quick smoke test: `python -c "import sounddevice as sd; print(sd.query_devices())"`

- [ ] **Write `cli/record.py`**

  A script that records from the microphone, saves the `.wav` file to `data/audio/`, and returns the file path.

  **Tips:**
  - Use `sounddevice.rec(duration * sample_rate, samplerate=sample_rate, channels=1)` with `sounddevice.wait()` for a simple blocking recording
  - For an Enter-to-start / Enter-to-stop flow, start recording in a thread and join it when the user hits Enter again — `sounddevice.InputStream` is good for this
  - Name files with a timestamp: `data/audio/{YYYY-MM-DD_HH-MM-SS}.wav`
  - Start with a hardcoded 60-second max; you can add dynamic stop later

- [ ] **Wire recording → transcription → console output**

  After saving the `.wav` file, `cli/record.py` should automatically call `services/transcriber.py` and print the transcript to the terminal.

  **Tips:**
  - Import and call `transcribe_audio(filepath)` from `services/transcriber.py` directly — the function already exists and works
  - Print the returned transcript string with a clear heading so it's readable in the terminal

- [ ] **Save the audio filename and raw transcript to the database**

  After transcription, persist a `log_segment` record so the data isn't lost between sessions.

  **Tips:**
  - The database functions already exist in `services/database.py` — call `create_or_get_log_header(date)` then `create_log_segment(entry_id, filename, duration, transcript)`
  - If you adopt SQLAlchemy (see Phase 2), wire this through a SQLAlchemy session instead of the raw helper

---

## Phase 4 — LLM Enrichment & Markdown Output

- [ ] **Update `cli/record.py` to run formatting automatically after transcription**

  Once a recording is saved and transcribed, `record.py` should call the LLM formatter and save the resulting Markdown — without any manual steps.

  **Tips:**
  - The LLM formatter already exists in `services/llm_client.py` (`llm_formatter()`). Import and call it after transcription completes
  - Write the returned Markdown string to `data/logs/{YYYY-MM-DD}.md`, creating the file if it doesn't exist or overwriting it if it does
  - This step can be slow — print a "Formatting…" status message before calling the LLM so the terminal doesn't feel frozen

---

## Phase 5 — Supplemental Recordings

- [ ] **Update `cli/record.py` to support append mode**

  When run a second time on the same day, `record.py` should detect an existing log entry and attach the new recording as a supplemental segment rather than creating a duplicate entry.

  **Tips:**
  - Call `create_or_get_log_header(today)` — it already returns the existing entry if one exists, so no extra logic is needed to detect duplicates
  - The multi-segment transcript combining logic is already in `services/database.py`'s `create_log_segment()` — the key is calling it rather than creating a new `log_entry` each time
  - After adding the segment, re-run the formatter with all of the day's combined transcripts and overwrite `data/logs/{YYYY-MM-DD}.md`

---

## Phase 6 — LLM Follow-Up Questions

- [ ] **Append follow-up questions to the day's Markdown file**

  After questions are generated and stored in the database, they should also appear as a section at the bottom of `data/logs/{YYYY-MM-DD}.md`.

  **Tips:**
  - Open the existing `.md` file in append mode (`open(path, "a")`) and write a `## Follow-Up Questions` section
  - The questions are stored as a JSON array in `log_enrichment.followup_qs` — use `json.loads()` to parse them and write each as a numbered list item (`1. question text`)
  - Do this after both the markdown and the questions are generated so the file is only written once per session
  - If a segment is added later in the day, clear the old questions section and rewrite it with the freshly generated set
