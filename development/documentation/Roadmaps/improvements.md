# Captain's Log — Suggested Improvements

Ideas for where to take the app next. These are organized by theme rather than effort, with a short explanation of *why* each one matters so you can decide which directions appeal to you.

---

## 1. Making the Past More Useful

Right now the app is good at capturing entries. It becomes genuinely powerful when you can retrieve and connect them. This section has the highest long-term return on investment.

---

### 1a. Full-Text Search

`pages/search_logs.py` exists but contains only a placeholder. This is the single most useful thing to add.

**Why it matters:** Journaling value compounds over time. Six months from now you'll want to find every entry where you mentioned a particular project, person, or problem. Without search, the history is just an archive. With search, it becomes a queryable record of your thinking.

**How to approach it:** The raw transcripts are already in the `log_segment` table. A `LIKE` query against `raw_transcript` gives you basic keyword search immediately. SQLite also has a built-in full-text search extension (`FTS5`) that's faster and handles partial words — worth exploring if the basic `LIKE` approach feels slow once you have hundreds of entries.

```python
# Basic approach using what's already there
results = session.execute(
    text("SELECT log_entry_id, raw_transcript FROM log_segment WHERE raw_transcript LIKE :term"),
    {"term": f"%{search_term}%"}
).fetchall()
```

---

### 1b. Calendar Heatmap

A visual grid showing which days have entries — similar to a GitHub contribution graph.

**Why it matters:** It makes your journaling habit visible. You can see gaps at a glance without paging through history. There's also a mild motivational effect: streaks are satisfying to maintain once you can see them.

**How to approach it:** The `entry_date` column in `log_entry` has everything you need. The `streamlit-calendar` library (`pip install streamlit-calendar`) can render a calendar view with marked dates. Alternatively, a simple grid of coloured squares built with `st.columns()` works well and has no extra dependency.

---

### 1c. Audio Playback in Log History

The original recordings are saved in `data/recordings/` with the filename format `YYYY-MM-DD-segmentID.wav`. The log history page could offer a playback button for each segment.

**Why it matters:** Reading a polished transcript and hearing your own voice are different experiences. Listening back occasionally is useful for noticing things the LLM cleaned up or changed, and for checking the quality of the transcription.

**How to approach it:** `st.audio(path_to_file)` is all it takes. You already have the filename stored in `log_segment.audio_filename`. The main work is joining the `log_segment` table when loading history entries so the filenames are available to the page.

---

### 1d. Entry Statistics Over Time

Show simple metrics derived from the data you're already capturing: entry count, total recording time, average entry length, entries per week.

**Why it matters:** Metrics make progress tangible. After three months of daily journaling you'll have accumulated far more than you realise — seeing "47 entries, 6.2 hours of audio" is satisfying in a way that's hard to get from reading individual entries.

**How to approach it:** All the raw data is in the database. `audio_duration` is stored per segment. `len(formatted_md)` gives word-count-ish metrics. A simple `st.metric()` row at the top of the history page or a dedicated stats section on the admin panel would work well.

---

## 2. Smarter Use of the LLM

The LLM is currently doing three things: formatting transcripts, generating follow-up questions, and producing weekly reviews. There are several meaningful extensions here.

---

### 2a. Cross-Entry Context for Follow-Up Questions

This was in the original roadmap but wasn't implemented. Currently the question generator receives only today's formatted entry. The original plan was to pass the previous 2–3 days' entries as context so the LLM could notice threads across days.

**Why this matters more than any other LLM change:** The whole point of a reflective journaling tool is to notice patterns across time. A question generated from today's entry alone asks "how do you feel about X?" A question generated with the last three days as context might ask "You've mentioned being frustrated with X three days in a row — what's actually driving that?" That's a fundamentally different quality of question.

**How to approach it:** The `get_weekly_transcripts()` function in `database.py` already retrieves transcripts for a date range. You could call it with the last 3 days before passing to the question generator:

```python
# In controller.py, after getting today's formatted_md:
context_start = (date.today() - timedelta(days=3)).isoformat()
context_end = (date.today() - timedelta(days=1)).isoformat()
recent_context = database.get_weekly_transcripts(context_start, context_end)

questions = llm_client.llm_question_generator(
    todays_entry=formatted_md,
    recent_context=recent_context   # update the function signature
)
```

Then update the system prompt in `llm_question_generator` to say: *"You will be given today's diary entry and the last few days' entries as context. Generate questions that notice threads and patterns across the entries, not just today's entry alone."*

---

### 2b. Theme and Topic Extraction

After formatting an entry, ask the LLM to extract 3–5 short topic tags from it (e.g., "work", "sleep", "project-alpha", "exercise"). Store them in the database and use them for filtering.

**Why it matters:** As the journal grows, search by keyword finds text but filter by theme finds meaning. Being able to say "show me all entries tagged #health over the last three months" is a qualitatively different capability.

**How to approach it:** Add a `tags` column to `log_enrichment`. Create a new LLM function (`llm_tag_extractor`) that returns a JSON array of 3–5 short lowercase strings. Run it as part of `process_log_entry()`. Display tags as chips on the log history page and let them act as filters.

---

### 2c. Mood and Energy Tracking

Ask the LLM to rate each entry on a simple 1–5 scale for mood and energy based on the content. Store and visualise these over time.

**Why it matters:** You chose voice journaling partly because it captures how you actually feel, not just what you consciously intended to say. A mood trend line across 30 days is the kind of insight that's genuinely hard to get any other way. You might notice that every Monday is a 2 and every Friday is a 4, or that your energy dips predictably mid-week.

**How to approach it:** Add `mood_score` and `energy_score` integer columns to `log_enrichment`. Create a new LLM function that extracts these from the formatted entry as a JSON object. Visualise with `st.line_chart()` or `st.bar_chart()` — both are built into Streamlit with no extra dependencies.

---

### 2d. Customisable Prompts via a Settings Page

Let you edit the system prompts used for formatting, question generation, and weekly review from within the UI — without touching the code.

**Why it matters:** The prompts are the highest-leverage variable in the whole system. A small change to the formatting prompt can produce dramatically different output. Right now, iterating on prompts means editing `llm_client.py` and restarting the app. A settings page would make this feel like configuration, not development.

**How to approach it:** The simplest version stores prompts as text files in a `prompts/` directory. The settings page displays them in `st.text_area()` fields and saves changes to disk. `llm_client.py` reads from those files instead of hardcoded strings. No database changes needed.

---

### 2e. Monthly and Quarterly Reviews

A natural extension of the weekly review. A monthly review gives you a different scale of reflection — not "what happened this week" but "what changed this month."

**Why it matters:** Weekly reviews zoom in on short-term patterns. Monthly reviews zoom out to longer arcs: projects that spanned weeks, habits that developed or faded, goals that were mentioned and then forgotten. The compound value of the journal grows as the review time windows grow.

**How to approach it:** The weekly review machinery already works. The date range picker on the weekly review page already accepts arbitrary ranges — technically a monthly review is already possible. The improvement is a dedicated UI section with pre-populated date ranges ("This month", "Last month", "Last quarter") and a separate prompt tuned for longer-range reflection.

---

## 3. Reducing Friction in the Daily Workflow

Small friction accumulates over time. A journaling tool that's slightly annoying to use gets used slightly less often.

---

### 3a. Recording for a Past Date

Currently, "Process recording" always uses today's date. If you make a recording at 11pm and process it the next morning, it's filed under the wrong day.

**Why it matters:** This will definitely happen during regular use. The fix is small but the frustration of discovering a misplaced entry is disproportionately annoying.

**How to approach it:** Add a `st.date_input()` to the record page, pre-filled with today's date but editable. Pass the selected date to `ctrl.process_log_entry()` instead of hardcoding `date.today()`. That's essentially the entire change.

---

### 3b. Regenerate Without Re-Recording

A button on Today's Log (or Log History) that re-runs the LLM formatting and question generation on the existing transcript, without needing to re-record.

**Why it matters:** Prompt engineering is an iterative process. When you improve the formatting prompt, you'll want to see how it affects existing entries — but currently you'd have to re-record them all. A "regenerate" button makes it trivial to refresh an entry.

**How to approach it:** `database.get_unified_transcripts(entry_id)` retrieves the combined transcript. Pass it through `llm_formatter()` and `llm_question_generator()` again, then call `database.upsert_log_enrichment()` and overwrite the markdown file. The existing `rebuild_database()` function in `controller.py` does a full version of this — a single-entry regenerate is a subset of that logic.

---

### 3c. Processing Status and Progress Feedback

The current processing flow redirects to Today's Log after completion with no indication of how long each step took or whether anything was slow.

**Why it matters:** Processing a recording currently takes 30–120 seconds (transcription + two LLM calls). With no progress indication other than the spinner, it's hard to know if the app is working or frozen. Explicit step-by-step feedback ("Transcription complete in 18s. Formatting... done in 34s.") also helps you understand where time is spent, which informs decisions like model size.

**How to approach it:** Use a status container in Streamlit:

```python
status = st.status("Processing recording...", expanded=True)
with status:
    st.write("Transcribing audio...")
    transcript, duration = transcriber.transcribe_audio(tmp_path)
    st.write(f"✅ Transcription done ({duration}s of audio)")
    
    st.write("Formatting with LLM...")
    formatted = llm_client.llm_formatter(transcript)
    st.write("✅ Formatting done")
    
    st.write("Generating follow-up questions...")
    questions = llm_client.llm_question_generator(formatted)
    st.write("✅ Questions done")

status.update(label="Done!", state="complete")
```

`st.status()` is a built-in Streamlit component designed exactly for this pattern.

---

### 3d. Answer Your Follow-Up Questions

The follow-up questions are currently a one-way output — they appear at the bottom of the entry but there's no mechanism to respond to them. Adding a voice response loop would complete the reflection cycle.

**Why it matters:** Generating questions is valuable. Answering them is where the actual reflection happens. Right now you have to remember to think about them outside the app. A simple "Answer today's questions" button on the record page — which creates a new recording tagged as a follow-up rather than a new entry — would close the loop.

**How to approach it:** This could be as simple as adding a "Follow-up recording" option on the record page that sets a flag indicating the recording is a response rather than a new entry. The combined transcript for the day would then include both the original entry and the responses, and the LLM would process them together.

---

## 4. Settings and Control

---

### 4a. Settings Page

The `pages/search_logs.py` stub could become or be joined by a settings page covering:

- **Whisper model size** (`tiny`, `base`, `small`, `medium`) — smaller models are faster but less accurate; worth being able to switch without editing code
- **Ollama model** — currently hardcoded as `gemma4:e4b`; you may want to experiment with other models
- **Number of context days** for follow-up questions (once cross-entry context is implemented)
- **Recordings directory path** — useful if you want to store audio on a different drive
- **Default date for new entries** — e.g. always use previous day before 6am

Store settings in a simple JSON file (`data/settings.json`). Load it at startup in `config.py`. The settings page reads and writes this file.

---

### 4b. Scheduled Daily Reminder

A desktop notification or terminal message at a set time reminding you to make an entry. The `schedule` library (or `APScheduler`, which is already mentioned in the roadmap) can run this in a background thread alongside the Streamlit app.

**Why it matters:** The biggest threat to a journaling habit isn't motivation — it's forgetting. A single prompt at 5pm asking "have you journaled today?" is often all that's needed.

---

## 5. Getting Data Out

---

### 5a. Export to a Single Document

Generate a single combined Markdown or PDF file covering a date range — useful for sharing a period with a coach or therapist, printing for review, or archiving.

**How to approach it:** Concatenate the markdown files for a date range in chronological order. For PDF, the `reportlab` or `weasyprint` library can convert Markdown → PDF. A Streamlit `st.download_button()` delivers the file directly to the browser.

---

### 5b. Obsidian / Notion Compatibility

The markdown files are already in a compatible format for Obsidian (a local-first note-taking app). Adding YAML frontmatter to each file would make them importable as proper Obsidian notes with metadata:

```markdown
---
date: 2026-05-08
tags: [work, health]
mood: 4
duration_seconds: 342
---

# Diary Entry for 2026-05-08
...
```

This costs very little to implement (just update the file-writing step in `controller.py`) and opens the door to Obsidian's graph view, backlinks, and plugin ecosystem as a read-only view of your journal.

---

## Where to Start

If you want a concrete recommendation: the improvements that will make the biggest difference to daily use, roughly in order, are:

1. **Full-text search** — the history is already growing; search is what makes it navigable
2. **Cross-entry context for questions** — the highest-impact LLM improvement; this is what makes the questions actually reflective
3. **Date override on recording** — small fix, eliminates a recurring annoyance
4. **Mood/energy tracking** — the most interesting insight that's currently inaccessible
5. **Calendar heatmap** — makes the habit visible, which tends to reinforce it
6. **Regenerate without re-recording** — unlocks safe iteration on prompts

The rest of the list ranges from "useful as the archive grows" (stats, tags, export) to "nice to have" (notifications, Obsidian export).
