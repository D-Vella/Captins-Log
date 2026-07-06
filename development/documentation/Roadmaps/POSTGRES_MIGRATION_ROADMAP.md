# Captain's Log — SQLite → PostgreSQL Migration Roadmap

> Move the database layer from a single SQLite file to a PostgreSQL server running as its own
> container, with the schema created automatically the first time the stack is deployed.
> Designed for spare-time development — each phase leaves the app fully working on whichever
> database backend it's currently pointed at, so you're never mid-migration with a broken app.

---

## Background & Goal

The app currently talks to a SQLite file (`db/application.db`) via a single hard-coded
connection string in `services/database.py`. A Postgres service is already stubbed into
`docker-compose.yaml` (commented "Under Development — not currently being used") and
`services/config.py` already reads `POSTGRES_DB/USER/PASSWORD/HOST/PORT` from `.env` — but
nothing in the app actually builds an engine from them yet. You've since stood up your own
Postgres container via Compose and confirmed connectivity, so the infrastructure side is ahead
of the application side.

Before any of that config gets wired up for real, two problems in the current code need fixing
regardless of which database you use — because they'd behave differently (or break outright) on
Postgres:

1. **There's no migration that actually creates the tables.** The only Alembic revision
   (`bd0bbe78a193_initial_schema.py`) only contains `add_column`/`alter_column`/`drop_column`
   calls against tables it assumes already exist — there's no `create_table` anywhere in the
   migration history. Running `alembic upgrade head` against a brand-new empty database fails
   immediately. This is the direct cause of needing a "database initialization on first deploy"
   step — right now there is no automated way to create the schema from nothing.
2. **The raw SQL in `services/database.py` has drifted from `services/models.py`.** The live
   code still writes to `duration_secs` and `generated_at`, columns the one migration explicitly
   renamed to `audio_duration`, `created_at`, and `updated_at`. This "works" today only because
   your SQLite file was never actually migrated in lockstep with the code — Postgres won't be so
   forgiving.

Both are fixed in Phase 1, on SQLite, before Postgres enters the picture at all — so if anything
breaks, you know it's the fix and not the new database.

---

## How To Use This Roadmap

Work top to bottom. Phases 1–3 are all still on SQLite — pure bug-fixing and prep, zero risk to
your working app. Phase 4 is the first point Postgres gets touched at all, and only manually.
Phase 5 is the one that matters most for your deployment: automatic schema creation on first
boot. Phases 6–7 are cleanup and can wait indefinitely. Do not start a phase until the previous
one's exit criteria all tick.

---

## Phase 1 — Fix the Cracks (Still on SQLite)
**Goal:** Resolve the schema drift and missing baseline migration while the database is still
SQLite, so these are ordinary bug fixes instead of migration-day surprises.
**Estimated effort:** 1–2 sessions

### Tasks
- [X] Decide the ground truth for the two drifted columns and fix the raw SQL in
      `services/database.py` to match `services/models.py`:
  - `create_log_segment()` — change the `INSERT` from `duration_secs` to `audio_duration`
  - `create_log_enrichment()` / `update_log_enrichment()` — change `generated_at` to
    `created_at` / `updated_at`
- [X] Delete your current SQLite file (or back it up) and rebuild it from a clean baseline so
      column names actually match — since it's dev data, this is simpler than writing a
      data-preserving `ALTER` script
- [X] Replace the single existing Alembic revision with one clean baseline migration that
      `op.create_table()`s all three tables exactly as they're defined in `services/models.py`
      today (this replaces `bd0bbe78a193_initial_schema.py` — you're the only consumer of this
      history, so squashing it is safe)
- [X] Run `alembic upgrade head` against a fresh, empty SQLite file and confirm all three tables
      appear with the correct columns
- [X] Run the app end-to-end (record → transcribe → enrich → browse history) against the rebuilt
      SQLite database and confirm nothing regressed

### Tips
- `alembic revision --autogenerate -m "initial schema"` against an empty DB with
  `target_metadata = Base.metadata` (already wired up in `alembic/env.py`) will generate the
  `create_table` calls for you — check the output before applying, autogenerate isn't perfect
- This phase touches no connection strings and no Docker files — if something breaks, it's the
  SQL change, not an environment difference

### Exit Criteria
`services/database.py` writes to the same column names `services/models.py` defines. A fresh
`alembic upgrade head` against an empty SQLite file produces a fully working schema with no
manual steps. The app works end to end against it.

---

## Phase 2 — Make the Engine Dialect-Aware
**Goal:** One place decides which database to connect to, driven by config — so switching
between SQLite and Postgres is an environment variable, not a code change.
**Estimated effort:** 1 session

### Background
Right now `services/database.py:7` hard-codes `f"sqlite:///{DATABASE_PATH}"` and `alembic.ini:89`
independently hard-codes a second, different SQLite URL. This phase collapses both into a single
function that builds the right SQLAlchemy URL from `services/config.py`, defaulting to SQLite so
nothing changes yet — Postgres isn't actually used until Phase 4.

### Tasks
- [X] Add a `DATABASE_BACKEND` value to `services/config.py` (env-driven via `.env`, default
      `"sqlite"`) alongside the existing `POSTGRES_CONFIG` dict
- [X] Add a `get_database_url()` function in `services/config.py` that returns
      `sqlite:///{DATABASE_PATH}` when the backend is `sqlite`, or builds
      `postgresql+psycopg2://user:password@host:port/dbname` from `POSTGRES_CONFIG` when it's
      `postgres`
- [X] Update `services/database.py` to call `get_database_url()` instead of building the string
      inline
- [X] Update `alembic/env.py` to call `get_database_url()` and inject it via
      `config.set_main_option("sqlalchemy.url", ...)` before `run_migrations_online()` builds the
      engine — this removes the second, independent connection string in `alembic.ini`
- [X] Confirm `alembic upgrade head` and the app both still work with `DATABASE_BACKEND=sqlite`
      (the default) — this phase should be invisible from the outside

### Tips
- Keep `psycopg2` import in `services/database.py` lazy or guarded if you want SQLite-only
  environments to not require it installed — though since `psycopg2-binary` is already in
  `requirements.txt`, this is likely a non-issue
- This is the phase to also delete the now-redundant `sqlalchemy.url` line in `alembic.ini` (or
  leave a comment explaining it's overridden by `env.py`) so there's exactly one source of truth

### Exit Criteria
Both the app and Alembic build their connection string from the same `get_database_url()`
function. With `DATABASE_BACKEND=sqlite` (default), everything behaves exactly as before —
this phase is a refactor, not a behavior change.

---

## Phase 3 — Postgres-Proof the Raw SQL
**Goal:** Remove the SQLite-only SQL so the exact same code path works unmodified against
Postgres, while still testing entirely against SQLite.
**Estimated effort:** 1 session

### Background
Two things in `services/database.py` rely on SQLite-specific behavior and will misbehave (one
loudly, one silently) the moment the backend is Postgres.

### Tasks
- [X] Replace `SELECT last_insert_rowid()` (`create_log_segment()`) with an `INSERT ... RETURNING id` and read the new ID off the `INSERT` result directly — `last_insert_rowid()` doesn't
      exist on Postgres, so this would fail hard the first time a segment is created
- [X] Fix the case-sensitivity assumption in `search_logs_by_keyword()` — it upper-cases the
      keyword in Python and relies on SQLite's default case-insensitive `LIKE`. Wrap the column
      side in `UPPER(...)` too (`WHERE UPPER(ls.raw_transcript) LIKE :keyword`) so the comparison
      is explicitly case-insensitive on both sides — this works identically on SQLite and
      Postgres, unlike switching to `ILIKE` (SQLite doesn't support `ILIKE` at all)
- [ ] Re-run the full app end-to-end against SQLite and confirm search and recording still work
      correctly — this phase should not change any observable behavior yet, only the SQL that
      produces it

### Exit Criteria
No SQLite-only SQL functions remain in `services/database.py`. Search and segment creation still
work correctly against SQLite. The same file could run against Postgres with zero further SQL
changes.

---

## Phase 4 — First Local Postgres Connection (Manual)
**Goal:** Prove the app actually works against your already-running Postgres container, by hand,
before any auto-initialization exists.
**Estimated effort:** 1 session

### Background
This is the first phase where Postgres is actually used. Since you've already confirmed
connectivity via your own Compose setup, this phase is about pointing the *app* — not just a
`SELECT 1` probe — at it.

### Tasks
- [ ] Fill in `.env` with real `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` /
      `POSTGRES_HOST` / `POSTGRES_PORT` values matching your Postgres container
- [ ] Set `DATABASE_BACKEND=postgres` in `.env`
- [ ] Run `check_connection("postgres")` (already exists in `services/database.py`) and confirm
      it returns `"OK"`
- [ ] Run `alembic upgrade head` against the empty Postgres database using the baseline migration
      from Phase 1 — confirm all three tables appear with `psql \dt` or a GUI client
- [ ] Run the app end to end against Postgres: record a segment, generate an enrichment, browse
      history, run a keyword search — fix anything that breaks
- [ ] Deliberately test the FK relationship — try creating a `log_segment` with a bogus
      `log_entry_id` and confirm Postgres rejects it (SQLite wasn't enforcing this without
      `PRAGMA foreign_keys=ON`, so this is a genuine new behavior worth seeing once on purpose)

### Exit Criteria
The app runs correctly end to end against Postgres with `DATABASE_BACKEND=postgres`, using
credentials from `.env`. Switching back to `DATABASE_BACKEND=sqlite` still works too — both
backends are live options at this point, selected by config alone.

---

## Phase 5 — Automatic Database Initialization on First Deploy
**Goal:** When the stack is deployed fresh — empty Postgres volume, brand new container — the
schema is created automatically. No SSH-in-and-run-alembic-by-hand step, ever.
**Estimated effort:** 1–2 sessions

### Background
Two separate problems have to be solved here, and it's worth keeping them distinct:

1. **Ordering** — the app container can start before Postgres is actually ready to accept
   connections, even if the `db` container has technically started. `depends_on` alone only
   waits for the container process to start, not for Postgres to finish its own startup.
2. **Schema creation** — even once Postgres is reachable, something has to actually run
   `alembic upgrade head` against it before the app tries to query tables that don't exist yet.

The standard pattern for both is a **healthcheck** on the `db` service (so Compose knows when
Postgres is actually ready) plus an **entrypoint script** on the `app` service (so migrations run
automatically every time the container starts, before the app process launches).

### Tasks
- [ ] Add a healthcheck to the `db` service in `docker-compose.yaml` using Postgres's own
      readiness tool:
  ```yaml
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5
  ```
- [ ] Change the `app` service's `depends_on` from a plain list to the long form so it actually
      waits for Postgres to be healthy, not just started:
  ```yaml
  app:
    depends_on:
      db:
        condition: service_healthy
  ```
- [ ] Reconcile the `db` service's hard-coded credentials (currently
      `POSTGRES_USER=captains_log_user`, etc., directly in `docker-compose.yaml`) with the
      `.env`-driven `POSTGRES_CONFIG` the app reads — both should come from the same `.env` file
      so the app and the database it's talking to always agree on credentials
- [ ] Write `entrypoint.sh` at the project root:
  ```bash
  #!/bin/sh
  set -e
  alembic upgrade head
  exec "$@"
  ```
- [ ] Update the `Dockerfile` to copy and use it:
  ```dockerfile
  COPY entrypoint.sh .
  RUN chmod +x entrypoint.sh

  ENTRYPOINT ["./entrypoint.sh"]
  CMD ["streamlit", "run", "app.py", \
       "--server.address", "0.0.0.0", \
       "--server.sslCertFile", "cert.pem", \
       "--server.sslKeyFile", "key.pem"]
  ```
- [ ] Test the actual scenario this phase exists for — wipe the Postgres volume entirely and
      bring the stack up from nothing:
  ```bash
  docker compose down -v
  docker compose up -d
  docker compose logs -f app
  ```
  Confirm the log shows Alembic creating tables before Streamlit starts, with no manual steps,
  and the app is usable immediately after
- [ ] Test the second most common real scenario — restart the stack **without** wiping the
      volume (`docker compose restart app`) and confirm `alembic upgrade head` running again
      against an already-current schema is a safe no-op

### Tips
- `alembic upgrade head` is idempotent — running it against a database that's already at the
  latest revision does nothing and exits cleanly, so it's safe to put in the entrypoint
  unconditionally on every container start, not just the first one
- If you want a visible safety margin beyond the healthcheck (e.g. Postgres reports healthy but
  briefly refuses new connections during its own crash-recovery replay), a small retry loop around
  the `alembic upgrade head` call in `entrypoint.sh` is a reasonable belt-and-braces addition —
  don't over-build this, a few retries with a short sleep is plenty for a single-node home setup
- Keep the SQLite path working through this phase too (`DATABASE_BACKEND=sqlite` should still
  boot fine without Postgres present) — you're not required to burn that bridge yet

### Exit Criteria
`docker compose down -v && docker compose up -d` on a completely empty Postgres volume results in
a fully working app with no manual `alembic` command ever typed by hand. Restarting the stack
without wiping the volume is equally clean.

---

## Phase 6 — Persistence & Backup for the Postgres Volume
**Goal:** The Postgres data survives container recreation and is actually backed up, not just
"technically persistent on local disk."
**Estimated effort:** 1 session

### Background
The `pgdata` named volume in `docker-compose.yaml` already survives `docker compose down` /
`up` cycles — but a named volume living only on the mini PC's local disk is exactly the situation
`DOCKER_DEPLOYMENT_ROADMAP.md` Phase D6 already solved once for the `data/`/`db/` folders. Worth
applying the same lesson here rather than treating the database as a special case.

### Tasks
- [ ] Decide whether `pgdata` stays a Docker-managed named volume (simplest, lives on the mini
      PC's local disk) or gets bind-mounted to a NAS path like the other volumes — a named volume
      is usually the right call specifically for Postgres, since database files are sensitive to
      the underlying filesystem's locking/fsync behavior and NAS mounts (especially over
      SMB/NFS) can cause corruption; if you want NAS-backed durability, back up *dumps*, not the
      raw data directory
- [ ] Add a simple `pg_dump` backup step — even a manual `docker exec` command you run
      periodically is a legitimate starting point:
  ```bash
  docker exec <db-container> pg_dump -U captains_log_user captains_log_db > backup.sql
  ```
- [ ] Decide where that dump file lands (NAS path makes sense here, since it's a portable SQL
      file rather than raw database files) and confirm it's included in existing NAS backup
      coverage
- [ ] Do one full restore-from-dump test into a throwaway Postgres container, so you know the
      backup actually works before you ever need it for real:
  ```bash
  docker exec -i <db-container> psql -U captains_log_user captains_log_db < backup.sql
  ```

### Exit Criteria
You know exactly where Postgres's data physically lives, you have at least one real `pg_dump`
backup taken, and you've proven — once — that restoring from it into a fresh container works.

---

## Phase 7 — Decommission SQLite
**Goal:** Once Postgres has been the daily driver for a while and you trust it, retire the
SQLite path so there's one database, one code path, one thing to reason about.
**Estimated effort:** 1 session — do this whenever, no rush

### Tasks
- [ ] If there's real log history in the old `db/application.db` worth keeping, write a small
      one-off script that reads all rows via the SQLite engine and re-inserts them via the
      Postgres engine (three tables, insert order `log_entry` → `log_segment` →
      `log_enrichment` to respect the foreign keys) — only needed once, then delete the script
- [ ] Remove the `./db:/app/db` volume mount from `docker-compose.yaml` now that SQLite isn't in
      the loop
- [ ] Decide whether to delete the SQLite branch of `get_database_url()` / `check_connection()`
      entirely, or keep it as a lightweight escape hatch for local dev without a Postgres
      container running — either is fine, just make the choice deliberately rather than by
      accident
- [ ] Update `Roadmap.md` Phase 2 (which currently documents SQLite as the chosen database) with
      a short note pointing at this document, so the project history stays accurate
- [ ] Remove `DATABASE_PATH` from `services/config.py` if the SQLite path is being fully retired

### Exit Criteria
Postgres is the only database the running stack talks to. Old SQLite data is either migrated
across or deliberately not needed. Project docs reflect Postgres as the actual storage backend.

---

## Field Notes
*Running log of discoveries, quirks, and decisions. Engineer's notebook, not polished docs.*

- [Date] — Ground truth chosen for `duration_secs` vs `audio_duration`, `generated_at` vs
  `created_at`/`updated_at`: [record decision here]
- [Date] — First `docker compose down -v && up -d` from empty volume: [record what broke, if
  anything]
- [Date] — Postgres FK enforcement caught: [record any orphaned-row surprises from Phase 4]
- [Date] — Backup/restore test result: [record outcome]

---

## Dependencies Reference

| Thing | Purpose | Notes |
|-------|---------|-------|
| `psycopg2-binary` | Postgres driver for SQLAlchemy | Already in `requirements.txt` |
| `postgres:16` image | Database container | Already stubbed in `docker-compose.yaml` |
| Alembic | Schema migrations, both backends | Already in `requirements.txt`; needs a real baseline migration (Phase 1) |
| `pg_isready` | Compose healthcheck | Ships inside the official `postgres` image, no extra install |
| `entrypoint.sh` | Runs migrations before app start | New file, Phase 5 |

---

## Principles To Keep In Mind

**Fix bugs before you change environments.** Phases 1–3 stay on SQLite on purpose — if something
breaks, you know immediately it's the code change and not a Postgres quirk.

**Idempotent migrations are what make automatic initialization safe.** `alembic upgrade head`
doing nothing on an up-to-date database is exactly what lets you run it unconditionally on every
container start, first deploy or the hundredth restart alike.

**A healthcheck beats a guess.** `depends_on` without a `condition: service_healthy` only checks
that a container process exists, not that Postgres is ready to accept connections — this is the
single most common cause of "works when I run it by hand, fails on a fresh `docker compose up`."

**Don't burn the SQLite bridge until you don't need it.** Keeping both backends selectable by
config through Phase 6 costs almost nothing and gives you a fallback the whole time you're
building confidence in Postgres.

**A backup you haven't restored from isn't a backup.** Phase 6's exit criteria requires an actual
restore test, not just a dump file sitting on a NAS share.
