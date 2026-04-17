# Captain's Log — Outstanding Tasks (Phases 1–6)

---

## Phase 2 — Database & Data Model

- [ ] **Install SQLAlchemy and Alembic, and migrate away from raw `sqlite3`**

  The project currently uses raw `sqlite3` cursor calls in `services/database.py`. The roadmap calls for SQLAlchemy (ORM) and Alembic (migrations) instead, which gives you type-safe models, easier query building, and a migration history as the schema evolves.

  **Tips:**
  - `pip install sqlalchemy alembic`
  - Run `alembic init alembic` from the project root to scaffold the migrations folder
  - Define SQLAlchemy models for `log_entry`, `log_segment`, and `log_enrichment` in a new `services/models.py`, then replace the raw `cursor.execute()` calls in `database.py` with `Session` operations
  - Once models exist, run `alembic revision --autogenerate -m "initial schema"` to generate your first migration from the existing schema
  - If you'd rather keep raw `sqlite3` permanently, update the roadmap to reflect that decision so this item stops being an open question

---

*All other Phase 1–6 tasks are complete. Next up: Phase 7 — FastAPI Backend.*
