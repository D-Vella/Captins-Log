# Captain's Log — Outstanding Tasks (Phases 6b & 7)

---

## Phase 6b — SQLAlchemy ORM Refactor

`services/models.py` defines proper SQLAlchemy ORM classes for all three tables, but `services/database.py` still talks to the database using raw `text()` SQL strings through the session. These tasks wire the two together.

- [ ] **Refactor `create_or_get_log_header()`**

  Replace the two raw `text("SELECT ...")` and `text("INSERT ...")` calls with ORM equivalents, and return the model object instead of a bare `int`.

  ```python
  from sqlalchemy import select
  from services.models import log_entry

  with Session() as session:
      entry = session.scalar(select(log_entry).where(log_entry.entry_date == entry_date))
      if not entry:
          entry = log_entry(entry_date=entry_date, created_at=now, updated_at=now)
          session.add(entry)
          session.flush()   # populates entry.id before commit
          session.commit()
      return entry          # or entry.id if callers need just the int for now
  ```

- [ ] **Refactor `create_log_segment()`**

  Replace the raw `INSERT` and the `GROUP_CONCAT` aggregation query. Use `session.add()` for the insert, then load all segments via the relationship and concatenate in Python.

  ```python
  new_segment = log_segment(
      log_entry_id=log_entry_id,
      audio_filename=audio_filename,
      audio_duration=int(duration_secs),
      raw_transcript=raw_transcript,
      created_at=now, updated_at=now
  )
  session.add(new_segment)
  session.commit()

  # Concatenate all transcripts in Python via the relationship
  entry = session.get(log_entry, log_entry_id)
  session.refresh(entry)
  return " ".join(s.raw_transcript for s in entry.log_segments)
  ```

- [ ] **Refactor `create_log_enrichment()`**

  Replace the raw `INSERT` with a `session.add(log_enrichment(...))`.

  ```python
  enrichment = log_enrichment(
      log_entry_id=log_entry_id,
      formatted_md=formatted_md,
      followup_qs=followup_qs,
      weekly_summary="",
      created_at=now, updated_at=now
  )
  session.add(enrichment)
  session.commit()
  ```

- [ ] **Refactor `reset_db()`**

  Replace the three raw `DELETE` strings. SQLAlchemy 2.0 style:

  ```python
  from sqlalchemy import delete
  from services.models import log_entry, log_segment, log_enrichment

  with Session() as session:
      session.execute(delete(log_enrichment))
      session.execute(delete(log_segment))
      session.execute(delete(log_entry))
      session.commit()
  ```

- [ ] **Verify notebooks still work**

  Run `cli/end-to-end.ipynb` top-to-bottom after the refactor and confirm the markdown file and database records are created correctly. Run `cli/recording_test.ipynb` too if a mic is available.

---

---

## Phase 7 — Streamlit UI

- [ ] **Install dependencies**

  ```bash
  pip install streamlit streamlit-audiorecorder
  ```

- [ ] **Create `app.py` at the project root and confirm it boots**

  ```bash
  streamlit run app.py
  ```

  Start with a bare `st.title("Captain's Log")` to verify the server runs before wiring in services.

- [ ] **Build the Record & Process page**

  Wire `streamlit-audiorecorder` (or `st.file_uploader`) → `transcriber.transcribe_audio()` → `llm_client.llm_formatter()` + `llm_client.llm_question_generator()` → `database` save → display results with `st.markdown()`.

  Use `st.session_state` to hold the transcript between the audio step and the LLM step so a page rerun doesn't re-trigger transcription. Wrap each slow call in `st.spinner()`.

- [ ] **Build the Today's Log view**

  Read `data/logs/{today}.md` from disk and render it with `st.markdown()`. If the file doesn't exist yet, show a prompt to make a recording.

- [ ] **Build the Log History page**

  Query `log_entry` records from the database, display as a list. Use `st.selectbox` or `st.radio` to pick an entry and render its Markdown.

- [ ] **Test end-to-end in the browser**

  Open `http://localhost:8501`, record or upload audio, and confirm the formatted log and follow-up questions appear.

---

*All Phase 1–6 tasks are complete. Complete Phase 6b (ORM refactor) before starting Phase 7 to keep the service layer clean.*
