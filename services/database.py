from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

DATABASE_URL = "sqlite:///../db/application.db"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def reset_db():
    with Session() as session:
        session.execute(text("DELETE FROM log_enrichment;"))
        session.execute(text("DELETE FROM log_segment;"))
        session.execute(text("DELETE FROM log_entry;"))
        session.commit()
    print("✅ Database reset successfully.")

def create_or_get_log_header(entry_date: str) -> int:
    with Session() as session:
        result = session.execute(
            text("SELECT id FROM log_entry WHERE entry_date = :date"),
            {"date": entry_date}
        ).fetchone()

        if result:
            return result[0]

        session.execute(
            text("INSERT INTO log_entry (entry_date, created_at, updated_at) VALUES (:date, :now, :now)"),
            {"date": entry_date, "now": datetime.now(timezone.utc)}
        )
        session.commit()
        return session.execute(
            text("SELECT id FROM log_entry WHERE entry_date = :date"),
            {"date": entry_date}
        ).fetchone()[0] # pyright: ignore[reportOptionalSubscript]

def create_log_segment(log_entry_id: int, audio_filename: str, duration_secs: float, raw_transcript: str) -> str:
    with Session() as session:
        session.execute(
            text("""INSERT INTO log_segment (log_entry_id, audio_filename, duration_secs, raw_transcript, created_at)
                    VALUES (:entry_id, :filename, :duration, :transcript, :now)"""),
            {"entry_id": log_entry_id, "filename": audio_filename,
             "duration": duration_secs, "transcript": raw_transcript,
             "now": datetime.now(timezone.utc)}
        )
        session.commit()
        print(f"✅ Log segment created for entry ID: {log_entry_id}")

        result = session.execute(
            text("SELECT GROUP_CONCAT(raw_transcript, ' ') FROM log_segment WHERE log_entry_id = :entry_id"),
            {"entry_id": log_entry_id}
        ).fetchone()

        return result[0] if result else raw_transcript

def create_log_enrichment(log_entry_id: int, formatted_md: str, followup_qs: str) -> None:
    with Session() as session:
        session.execute(
            text("""INSERT INTO log_enrichment (log_entry_id, formatted_md, followup_qs, generated_at)
                    VALUES (:entry_id, :md, :qs, :now)"""),
            {"entry_id": log_entry_id, "md": formatted_md,
             "qs": followup_qs, "now": datetime.now(timezone.utc)}
        )
        session.commit()