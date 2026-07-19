# Code Review v2 — Captain's Log after the Docker & Postgres Migration

**Date:** 2026-07-19
**Scope:** The whole repository as it stands on `main` (commit `44e92e0`), including the
Docker/compose setup, the CI workflow, the Alembic migrations, and everything in
`services/` and `pages/`. Where `code_review_v1.md` already covered something, I track
whether it was fixed rather than repeating the full explanation.

This is written as a peer review: what you did well, what's broken, what to improve,
and — since you asked — an honest read on where you are as a Python programmer and
what to work on next.

---

## 1. The Big Picture

For a first GitHub project, a first Docker project, a first SQL project, and a first
LLM project *simultaneously*, this is genuinely impressive. The things that are hard
to teach are already present:

- **The layering is real, not decorative.** Pages talk to the controller, the
  controller orchestrates services, services don't know Streamlit exists. When I
  needed to understand the processing pipeline I read `process_log_entry()` once,
  top to bottom, and understood the whole system. That's what good structure buys you.
- **You migrated a live system from SQLite to Postgres in phases, with Alembic,
  behind an env-var switch, without a rewrite.** That's a professional-grade move.
  Most self-taught developers would have forked the project or done a big-bang rewrite.
  The `entrypoint.sh` running `alembic upgrade head` before the app starts is exactly
  the right pattern.
- **The documentation habit is your superpower.** `learning_points.md`, the phased
  roadmaps, the migration roadmap, keeping the old code review in the repo — this is
  rarer than good code. It compounds: you can see your own bug patterns (the
  `fetchone()` row-vs-scalar trap appears in both the learning points and the v1
  review, and the fixed `upsert_log_enrichment()` shows you internalised it).
- **CI that builds and pushes a tagged, cached image to GHCR** is a real deployment
  pipeline. Tagging with both `latest` and the commit SHA means you can always roll
  back to a known image. Many working developers don't have this on their side projects.

The main themes of this review, previewed up front:

1. Several pages are currently **broken at runtime** (nested expanders, the compose
   file, the admin panel's date handling) — things that would be caught instantly by
   even one automated test or a quick manual pass through each page.
2. The project has **zero tests**, and it's now at the size where that's the single
   highest-leverage improvement.
3. A recurring pattern of **swallowing errors and lying to the caller** (returning
   success paths after failures, `pass` stubs behind working-looking UI, `# type: ignore`
   to silence the type checker instead of fixing the type).

---

## 2. Report Card — What Happened to the v1 Review Items

| v1 item | Status |
|---|---|
| `upsert_log_enrichment()` row-vs-scalar bug | ✅ **Fixed** — and fixed correctly, extracting `[0]` and handling the no-row case |
| `LOGS_DIR` duplicated in three files | ✅ **Fixed** — pages now import from `services.config` |
| Unused import in `todays_log.py` | ✅ **Fixed** |
| Models vs raw SQL schema divergence | ✅ **Mostly fixed** — columns now agree; Alembic generates from the models |
| `api_delete_log_entry()` is a stub | ❌ **Still a stub** — the admin panel still shows "Entry deleted." while doing nothing |
| Temp files never cleaned up (`record.py`, `tools.py`) | ❌ **Still leaking** |
| "Process recording" crashes with no audio | ❌ **Still crashes** |
| Weekly review cache never invalidated | ❌ **Still stale after generating** |
| Imports inside functions/if-blocks | ❌ **Still present** (`record.py`, `controller.py`, `llm_client.py`, `transcriber.py`) |
| `camelCase` variables in `llm_client.py` | ❌ **Still present** |
| `json` imported twice in `llm_client.py` | ❌ **Still present** |
| `log_enrichment.back_populates="log_enrichments"` missing attribute | ❌ **Still present** — will raise the moment the ORM relationship is used |
| Model class names should be `PascalCase` | ❌ **Still present** |

Four fixed, nine outstanding. The ones you fixed were the data-corruption ones, which
was the right prioritisation. But notice that the outstanding ones are all "known and
written down but not done" — see §7 on process.

---

## 3. New Bugs

Ordered roughly by severity. "New" means introduced or surfaced since the v1 review,
mostly by the Docker/Postgres migration and the new pages.

### 3.1 `docker-compose.yaml` — `depends_on` is invalid and `docker compose up` will refuse to start

```yaml
depends_on:
  - db:
    condition: service_healthy
```

This parses as YAML, but as a *list containing a mapping* —
`[{db: None, condition: service_healthy}]`. The Compose schema allows either a list of
strings (`- db`) or a mapping; a list of mappings fails validation, so the whole stack
won't come up. You want the mapping form, since you're using `condition`:

```yaml
depends_on:
  db:
    condition: service_healthy
```

Side observation: the comment on the `db` service says "Under Development and not
currently being used", but `depends_on` (once fixed) makes the app refuse to start
until Postgres is healthy. One of those two statements is stale — worth reconciling.

### 3.2 Nested expanders crash `log_history.py` and `search_logs.py`

Streamlit does not allow an `st.expander` inside another `st.expander` — it raises
`StreamlitAPIException` at render time. `log_history.py` nests three deep
(entry → "View log data" → "Audio Recordings"/"Transcript"), and `search_logs.py`
nests two deep (date → "Transcript").

In `log_history.py` the outer `try/except` catches it and displays the exception, so
the page shows a red traceback instead of your history the moment one entry exists.
In `search_logs.py` there's no catch, so the first successful search errors out.

**Fix options:** replace the inner expanders with `st.tabs(["Log", "Transcript", "Audio"])`,
or use `st.popover`, or just flatten to headed sections inside the one expander. Tabs
are probably the nicest fit here.

This is also a lesson about that `try/except st.exception(e)` wrapper: it converted a
loud, immediate development-time failure into a page that "sort of renders", which is
probably why this survived. Catch-all exception handlers at page level hide bugs;
during development you generally want pages to fail loudly.

### 3.3 `log_history.py` reads the markdown file before checking it exists

```python
st.download_button(..., data=log_file.read_bytes(), ...)   # ← raises if missing
...
if log_file.exists():                                       # ← checked too late
```

`read_bytes()` on a missing file raises `FileNotFoundError`, which the outer
`try/except` turns into a full-page error — so **one** entry without a markdown file
(e.g. a DB row whose `.md` was deleted, or a rebuild that failed halfway) kills the
entire history page for every other entry. Move the `exists()` check above the
download button, and prefer per-entry error handling over one page-wide try.

### 3.4 Admin panel: `api_get_logs("")` returns a dict keyed by list index, and the page treats the keys as dates

`api_get_logs` returns `{0: {...}, 1: {...}, ...}` — the keys are `enumerate()`
indices. The admin panel then does:

```python
dates = sorted(headers.keys())
st.caption(f"Earliest entry: {dates[0]}  |  Latest entry: {dates[-1]}")   # "Earliest entry: 0 | Latest entry: 14"

selected_date = st.selectbox("Select entry to manage", options=sorted(headers.keys(), reverse=True), ...)
```

So the overview caption shows integers, and the entry-management dropdown offers the
user `14, 13, 12, ...` instead of dates. Then `api_delete_log_entry()` is called with
that index — though since it's still `pass`, nothing happens anyway. Three layers of
"looks like it works": a working confirm dialog, a success toast, a cleared cache — and
no delete.

**Root cause worth absorbing:** the index-keyed dict is an awkward return shape. A
plain `list[dict]` is what this function naturally returns; if you need date lookup,
key by `entry_date`. When a function's return shape needs a comment to explain, the
callers will eventually guess wrong — which is exactly what happened here.

### 3.5 `get_weekly_transcripts()` will likely fail on Postgres — date parameters vs a string column

`log_entry.entry_date` is a `String(25)` column, but `get_weekly_transcripts()` binds
Python `date` objects:

```python
WHERE entry_date BETWEEN :start_dt AND :end_dt   -- varchar vs DATE
```

SQLite is typeless enough to let this work. Postgres is not: psycopg2 sends those
parameters as dates, and Postgres has no implicit `varchar >= date` comparison, so
this raises `operator does not exist: character varying >= date`. Your Weekly Review
page most likely broke when you flipped `DATABASE_BACKEND` to `postgresql` — test it.

The immediate fix is to bind ISO strings (`start_date.isoformat()`), which compares
correctly *because* ISO-8601 strings sort chronologically. The real fix is §5.1:
`entry_date` should be a `Date` column. This bug is the migration telling you that.

### 3.6 `check_connection("sqlite")` doesn't check SQLite

`database.check_connection()` branches on a `db_type` argument, but the `"sqlite"`
branch uses the module-level `engine` — which is built from `get_database_url()` and
therefore points at *whatever backend is configured*. Since the migration, "SQL_Lite_database: OK"
in the admin connectivity check actually means "Postgres reachable via SQLAlchemy",
and the `"postgres"` branch re-checks the same server via raw psycopg2. Neither label
is true, and this is the only reason `psycopg2` is imported directly at all.

Suggested shape: one `check_database()` that checks the *configured* engine and reports
which backend it is:

```python
def check_database() -> str:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return f"OK ({engine.dialect.name})"
    except Exception as e:
        return f"Connection failed: {e}"
```

That deletes the direct psycopg2 dependency from your code, kills the misleading
labels, and (with `psycopg2-binary` staying in requirements as the driver) might
also end the "fixed the bloody psycopg again" commits.

### 3.7 `transcription_cleanup()` — `UnboundLocalError` on an unexpected mode

```python
if mode_choice == "Transcription Cleanup":
    system_prompt = cleanup_prompt
elif mode_choice == "Note Taking":
    system_prompt = note_taking_prompt

cleanup_response = call_llm_api(prompt=prompt, system=system_prompt, ...)
```

Any other `mode_choice` value leaves `system_prompt` unassigned →
`UnboundLocalError`. Today the UI constrains the value, but the function shouldn't
rely on that. Either `else: raise ValueError(...)`, or better, replace the chain with
a dict — which also removes the stringly-typed coupling to the UI labels:

```python
PROMPTS = {"Transcription Cleanup": cleanup_prompt, "Note Taking": note_taking_prompt}
system_prompt = PROMPTS[mode_choice]   # KeyError names the bad value for free
```

### 3.8 `call_llm_api()` has no timeout — a hung Ollama call hangs the app forever

`requests.post(f'{LLM_ENDPOINT}/api/chat', json=payload)` with no `timeout=` will wait
indefinitely if the server accepts the connection but stalls (which local LLM servers
under load absolutely do). The connectivity *check* has a 2-second timeout, but the
call that matters has none. Give it a generous one (`timeout=600`) so a wedged server
becomes a visible error instead of a frozen page.

Related, in the same function:
- It uses `requests` while everything else in the project uses `httpx` — pick one
  (httpx, since you already depend on it) and drop `Requests` from requirements.
- The line-by-line `splitlines()` parsing is streaming-response code, but you send
  `"stream": False`, so the body is a single JSON object: `api_response.json()["message"]["content"]`
  replaces the whole loop.
- `format` shadows the built-in `format()`; call it `response_format`.
- No `raise_for_status()` — a 404/500 from Ollama currently surfaces as a confusing
  JSON parse error rather than an HTTP error.

### 3.9 `weekly_review.py` — selecting a single date silently does nothing

`st.date_input` with a range value returns a 1-tuple while the user has only picked
the start date. The button handler checks `len(date_range) == 2` and otherwise falls
through with no message. Add an `else: st.warning("Pick both a start and end date")`.
Also, the v1 cache bug is still here: after generating, call
`load_weekly_reviews.clear()` or the new review won't appear until restart.

### 3.10 `get_unified_transcripts()` concatenates segments with no separator

The `'\n\n'` is appended once after the loop, so two recordings in one day produce
`...end of first sentenceStart of second...` — glued words that then flow into the
LLM formatting prompt and search. Join inside the loop:
`'\n\n'.join(t[2] for t in transcripts)`.

### 3.11 `search_logs_by_keyword()` returns duplicate rows

The query joins `log_entry × log_segment × log_enrichment`, so an entry with 3
segments appears 3 times in results (× N if duplicate enrichment rows exist from the
pre-fix upsert era). Either search the unified text per entry, or
`SELECT DISTINCT le.id, le.entry_date, lech.formatted_md` and show the enrichment
rather than per-segment raw transcripts.

### 3.12 `app.py` — `init_database()` is dead code, and so is the `pages` list

`init_database()` is defined but never called (harmless, since `entrypoint.sh` now
runs Alembic — but a reader can't tell whether that's intentional). The `pages` list
is built and never passed to `st.navigation()`; navigation currently works only
because Streamlit auto-discovers the `pages/` directory. Either commit to the
`st.navigation` API (which gives you control over titles, icons, and ordering — and
would let you hide `admin_panel` behind a flag) or delete the list. Half-adopted
mechanisms are worse than either choice.

---

## 4. Security & Deployment Notes

These matter more now that the image is published and the app serves your private
journal over the network.

### 4.1 A private TLS key is baked into the public GHCR image

The `Dockerfile` runs `openssl req ... -keyout key.pem` at **build** time, so every
image pushed to `ghcr.io/d-vella/captains-log` contains that private key — and the
build log/image is public. Anyone can pull the image, extract `key.pem`, and
impersonate `melody`/`192.168.0.119` on your network. The compose file then mounts
host-side `./cert.pem`/`key.pem` over them anyway, so the baked ones are both
dangerous *and* unused.

**Fix:** delete the `openssl` step from the Dockerfile and generate the cert on the
host (or in `entrypoint.sh` if the pem files are absent). Also note the Dockerfile
hardcodes your LAN IP and hostname into a public image — not dangerous by itself,
just unnecessary disclosure.

### 4.2 `.env` is mounted into the container for no reason

`- ./.env:/app/.env:ro` — nothing in the app reads `.env` (all config comes from
`os.getenv`, which compose's `environment:` block populates). Mounting the secrets
file into the container just widens the blast radius if anything in the container is
ever compromised. Drop the mount. (Alternatively, switch the service to `env_file: .env`
and delete the eleven `environment:` lines — one mechanism, not two.)

### 4.3 No authentication on the app

Streamlit on `0.0.0.0:8501` with TLS but no auth means anyone on your LAN can read
your journal and hit the admin panel's "Rebuild Database" button. For a home network
this may be an accepted risk, but it's worth being deliberate: options in ascending
effort are binding to localhost + Tailscale/WireGuard, a reverse proxy (Caddy gives
you basic-auth + real TLS in ~5 lines), or Streamlit's newer built-in auth. At minimum
I'd put the admin panel behind *something*.

### 4.4 Database password goes unescaped into the URL

`f"postgresql://{user}:{password}@..."` breaks if the password ever contains
`@ : / %`. Use `sqlalchemy.engine.URL.create(...)`, which handles quoting and is the
canonical way to build these.

### 4.5 Dockerfile miscellany

- The whole file is indented by two spaces — Docker tolerates it, but it will trip
  up copy-paste and some linters (`hadolint` is worth running once).
- `COPY entrypoint.sh .` is redundant — `COPY . .` already brought it in. Do
  `RUN chmod +x` on the existing copy, or better, `git update-index --chmod=+x entrypoint.sh`
  so it's executable in the repo itself.
- Consider a non-root `USER` and a `HEALTHCHECK` (Streamlit serves
  `/_stcore/health`) — both are cheap and standard.
- The `.dockerignore` is good (data, db, pem, env all excluded). Nice touch that
  many people miss.

---

## 5. Design & Data Model

### 5.1 `entry_date` should be a `Date` column with a unique constraint

It's the natural key of your whole data model, yet it's `String(25)`, nullable-ish in
spirit, and un-unique. Consequences already visible: the Postgres comparison bug
(§3.5), string-typed function signatures throughout (`entry_date: str`), and
`create_or_get_log_header()` doing check-then-insert with no constraint backstop (a
duplicate day is *possible* — nothing in the schema forbids it; the roadmap's original
SQL had `UNIQUE` but it never made it into the model). One Alembic migration fixes
all of it: `sa.Date(), nullable=False, unique=True`. This is the single most valuable
schema change available to you, and doing it via a real data migration (cast existing
strings to dates) would be an excellent Alembic exercise.

### 5.2 Commit to the ORM or delete `models.py` from runtime

Right now the models exist to feed Alembic autogenerate — which is legitimate! — but
`database.py` is 350 lines of raw `text()` SQL with hand-rolled row-to-dict mapping,
`# pyright: ignore` on unsafe subscripts, and per-function `Session()` blocks. Your
own `TO-DO.md` Phase 6b describes the refactor and even contains correct sample code.
The longer the raw SQL grows (it grew by ~6 functions since v1), the bigger that
refactor gets. I'd do it next, before adding features: it deletes the
`row[0]`/`row[2]` indexing class of bug (the one you keep hitting), fixes the
relationship bug (§2, `back_populates`) as a side effect, and makes functions return
typed objects instead of tuples-you-must-remember-the-shape-of.

### 5.3 The filesystem and the database are two sources of truth

Markdown files in `data/logs/`, recordings in `data/recordings/`, and rows in
Postgres all describe the same entries, connected only by filename conventions
(`YYYY-MM-DD.md`, `YYYY-MM-DD-segmentID.wav`, `file[:10]` slicing in
`rebuild_database`). You've handled it carefully, but the seams show: history pages
break when an `.md` is missing (§3.3), weekly reviews live only as files
(`get_weekly_reviews` globs the directory) while the `weekly_summary` DB column sits
unused, and deletion (once implemented) has to remember to clean up three places.
Direction to consider: make the database authoritative — store the formatted markdown
you already have in `log_enrichment.formatted_md` as the source, render pages from
the DB, and treat the `.md` files purely as *export* artifacts. That would also make
"Today's Log" show any selected day trivially.

### 5.4 Error-handling philosophy: stop returning success after failure

The clearest example is still `save_uploaded_audio()`: every exception path prints an
emoji to a terminal nobody is watching and then **returns the destination path
anyway**, so the DB can reference audio that was never saved and a later rebuild
quietly loses that day. Same family: `api_delete_log_entry` (§3.4) reports success
for a no-op, and the page-level `try/except` in log history (§3.2) converts crashes
into half-rendered pages. The rule that serves you better: *let exceptions propagate
to the layer that can actually do something about them* — in this app, that's the
Streamlit page, which can `st.error(...)` honestly. A function should either succeed
or raise; "print and continue" is the one option that's never right.

### 5.5 `print()` → `logging`

There are ~20 `print()` calls across services. In Docker they end up in
`docker logs` untimestamped and unlevelled. Python's `logging` module with one
`basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")`
in `app.py` and `logger = logging.getLogger(__name__)` per module is a 30-minute
change that pays off every time you debug the deployed container. Keep the emojis if
you like them — logging doesn't mind.

---

## 6. Smaller Code-Quality Items (new since v1)

- **`services/printer.py` doesn't belong in `services/`** — it imports
  `IPython.display` and is notebook tooling. Move it to `development/`, and then
  `ipython` can leave `requirements.txt` (it's currently a production dependency of
  your Docker image just for this).
- **`api_get_logs`**: `session.close()` after the `with Session()` block is redundant
  (the context manager already closed it); the `len(log_id) == 0` sentinel would be
  cleaner as `log_id: int | None = None`; and the `api_` prefix on half the DB
  functions suggests a REST API that doesn't exist (yet — see §8.5). Prefix by what
  it *is*, not what page calls it.
- **`get_dated_entry_id` lies in its signature** — `-> int` but returns `None` on
  miss, silenced with `# type: ignore`. Declare `-> int | None` and handle the miss in
  `log_history.py`. Rule of thumb worth adopting: every `# type: ignore` /
  `# pyright: ignore` is the type checker telling you something true; silencing it is
  borrowing against a future runtime error (§3.5 is what that debt looks like when
  called in).
- **`== None`** → `is None` (`llm_client.py`, three places). Also those checks are
  dead code — `call_llm_api` can't return `None`.
- **Duplicate "today's log" rendering** — `record.py` re-implements what
  `todays_log.py` does. Extract a `render_log_for(date)` helper or link to the page.
- **`ensure_directories()` per-request** — harmless, but it belongs in startup
  (`entrypoint.sh` or `app.py`), not inside `process_log_entry`.
- **`create_or_get_log_header` re-SELECTs after INSERT** while `create_log_segment`
  correctly uses `RETURNING id`. Make the header function match — one style, the
  better one.
- **`check_connections()` result keys** — `"SQL_Lite_database"`, `"Postgress_database"`:
  typos in user-visible output; also see §3.6 for making it one honest check.
- **`transcribe_audio()` stub in `controller.py`** returns the string
  `'Not Implemented'` — if anything ever calls it, that string would flow onward as if
  it were a transcript. Stubs should `raise NotImplementedError`, never return
  plausible data. (Same lesson as §3.4, in miniature.)
- **Repo name** — "Captins-Log" is missing its *a* (Captain's). GitHub repo renames
  redirect old URLs automatically, so it's a safe fix if it bothers you; the image
  name `captains-log` already spells it right, which is how I noticed.

---

## 7. The Biggest Gap: No Tests

This is the most important section of the review.

Every bug in §3 — the compose file, the nested expanders, the index-keyed dict, the
Postgres date comparison — would have been caught before commit by either a tiny test
suite or a five-minute click-through of each page. You don't have a testing problem
because testing is hard; you have one because the project grew past the size where
"run it and see" covers the surface area. That's a milestone, not a failure.

What makes your codebase *unusually easy* to test is the layering you already built:
`services/` has no Streamlit in it, so it can be tested with plain `pytest` and an
in-memory SQLite database, no UI harness needed. Concretely, a first suite:

```
tests/
├── conftest.py           # fixture: engine → sqlite:///:memory:, run Alembic, yield Session
├── test_database.py      # create_or_get_log_header is idempotent per date;
│                         # upsert_log_enrichment inserts-then-updates (regression-test your v1 bug!);
│                         # get_unified_transcripts separates segments;
│                         # search_logs_by_keyword returns one row per entry
├── test_llm_client.py    # question-generator parsing: plain JSON, ```-fenced JSON, garbage → ValueError
│                         # (pure string-wrangling — no live LLM needed)
└── test_controller.py    # process_log_entry with transcriber+llm monkeypatched:
                          # right rows exist, .md written, temp/audio files in the right place
```

Then add ~10 lines to `build.yml` so `pytest` (and `ruff check` — it would have
flagged the unused imports, `== None`, and the shadowed `format` for free) run *before*
the Docker build, and a red ❌ on GitHub stops a broken image from ever reaching GHCR.
That turns your existing CI from "packaging" into an actual safety net, and it's the
practice that most accelerates you as a developer: writing testable code changes how
you design code.

One habit-level observation to pair with this: §2 shows the fixed/unfixed split — the
v1 items that got fixed were the ones with data-loss stakes; the "small" ones (temp
files, the no-audio crash, the cache) have now survived two review cycles while new
features shipped. Known bugs rot into permanent fixtures this way. A rule like
*"every third session is a bug-fix session"* — or simply turning each open review item
into a GitHub Issue so they're visible on the repo instead of in a doc — would close
that loop. You already run phases with exit criteria; make "review findings addressed"
an exit criterion.

---

## 8. Feature Ideas Worth Considering

Your `improvements.md` already lists good ones (FTS, calendar heatmap, tags,
export). Building on those rather than repeating them:

1. **Backups — now urgent, and now easy.** Postgres in a Docker volume is one
   `docker compose down -v` away from gone, and it holds your journal. A nightly
   `pg_dump` to `data/backups/` (a second tiny compose service, or a cron on the
   host) plus copying that directory anywhere off-machine is an evening's work.
   I'd do this before any feature.
2. **Postgres full-text search.** The migration unlocked `tsvector`/`tsquery` —
   proper stemmed, ranked search with a GIN index, no new dependency. It would replace
   the `LIKE` scan in `search_logs_by_keyword` and fix §3.11 naturally
   (`ts_rank` + `DISTINCT ON (log_entry_id)`).
3. **Semantic search / "related entries."** You already run Ollama; it can serve
   embedding models (e.g. `nomic-embed-text`). Embed each entry, store the vector
   (pgvector extension), and "show me entries where I felt like this" becomes
   possible. This is the feature that makes a year of journaling compound, and it's a
   perfect learning project for the LLM side of your stack.
4. **Ask-my-journal (RAG).** Once §8.3 exists, "What was I worried about in March?"
   is retrieval + one LLM call. Natural culmination of the whole architecture.
5. **A real API layer.** The `api_*` naming and your roadmap's original `api/` folder
   both point at FastAPI. A thin FastAPI service over the controller would let you
   post recordings from your phone (Shortcuts/Tasker) without opening the web UI —
   which, for a daily-habit app, might be the single biggest usability win.
6. **Streak/heatmap on Today's Log** — from `improvements.md`, seconded; it's the
   cheapest motivational feature and `entry_date` already holds everything needed.
7. **Editable follow-up answers.** The LLM asks reflection questions, but there's
   nowhere to answer them. A text box that appends your answers to the entry would
   close the reflection loop the questions are for.

---

## 9. About You as a Programmer

You asked for feedback on your capabilities, not just the code, so — based on the
code, the docs, and the git history:

**Where you're genuinely strong.** Architecture instinct (the layering was the right
call and you stuck to it under pressure of features); operational thinking (env-var
config switch, migrations at container start, image tagging by SHA — you think about
*running* software, not just writing it); learning process (roadmaps with exit
criteria, learning-points journal, keeping reviews in-repo — you treat your own
development as a project, which is exactly how senior engineers improve); and scoping
(each phase shipped something usable; the project never wandered).

**The growth edges, in priority order:**

1. **Finishing discipline over starting energy.** The codebase has a consistent
   pattern: the happy path is built well, then attention moves on before the edges are
   sealed — stubs behind working UI, error paths that print and pretend, known bugs
   surviving review cycles. The gap between "works when I use it right" and "works" is
   where professional code lives, and it's currently your widest gap. The fix isn't
   talent, it's process: tests (§7), and treating review findings as queue items
   rather than reading material.
2. **Trust the exception system.** Multiple places catch exceptions only to print and
   continue, or return sentinel values (`'Not Implemented'`, a path that isn't there,
   `{}`). Python's exceptions *are* the error-reporting channel; code gets shorter
   and safer when you let them fly to the layer that can respond. Re-read §5.4 —
   internalising that one principle would eliminate a third of this review.
3. **Consistency as a habit.** `httpx` and `requests`; `snake_case` and `camelCase`;
   `RETURNING id` and re-SELECT; `st.navigation` half-adopted; ORM models beside raw
   SQL. Each inconsistency is small; together they mean every reader (including
   future-you) must hold two ways of doing everything. When you touch code that does
   X two ways, leave it doing X one way.
4. **Listen to the type checker.** You clearly run pyright — but the `ignore` comments
   show you negotiating with it rather than obeying it. Its complaints in this
   codebase were all correct predictions of real bugs.

None of these are unusual — they're the standard edges for someone at your stage, and
the foundation underneath them (architecture, ops, process) is *stronger* than usual.
The typical self-taught path produces people who write clever code with no structure;
you've built structure first, which is much harder to retrofit. Add tests and
finishing discipline and the rest follows.

---

## 10. Prioritised Action List

**Broken right now (do first):**
1. Fix `depends_on` in `docker-compose.yaml` (§3.1) — the stack won't start as committed.
2. Replace nested expanders with tabs in `log_history.py` and `search_logs.py` (§3.2).
3. Move the `log_file.exists()` check above the download button (§3.3).
4. Fix or bind-as-string the weekly-transcript date query and test Weekly Review on Postgres (§3.5).
5. Fix the admin panel's index-keys-as-dates handling and implement `api_delete_log_entry` (§3.4).

**Security (same week):**
6. Remove cert generation from the Dockerfile; generate keys on the host (§4.1).
7. Drop the `.env` volume mount (§4.2); decide on an auth story for the admin panel (§4.3).

**Foundations (next phases):**
8. Stand up `pytest` + `ruff`, wire them into `build.yml` before the image build (§7).
9. Clear the v1 leftovers in one sweep: temp-file cleanup, no-audio guard, weekly-review cache, top-level imports, naming (§2).
10. Alembic migration: `entry_date` → `Date`, `unique=True` (§5.1).
11. Phase 6b ORM refactor of `database.py` (§5.2).
12. Nightly `pg_dump` backups (§8.1).

**Then have fun:** Postgres FTS → embeddings → ask-my-journal (§8.2–8.4).
