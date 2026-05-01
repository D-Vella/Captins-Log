from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, date
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{_BASE_DIR}/db/application.db"

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

def api_get_logs(log_id:str):
    """
    Api call to return a specifc log or a list of logs.
    args: log_id = a string of the log identifer.
    """
    
    with Session() as session:
        if len(log_id) ==0:
            results = session.execute(
                text("""
                        SELECT id, entry_date, created_at
                     FROM log_entry
                    """)
            ).fetchall()
        
        else:
            results = session.execute(
                text("""
                        SELECT id, entry_date, created_at
                     FROM log_entry
                     WHERE id = :log_id
                     """),
                     {"log_id": log_id}
            ).fetchone()
    
    session.close()

    if not results:
        return None

    def row_to_dict(row):
        return {'id': row[0], 'entry_date': row[1], 'created_at': str(row[2])}

    if len(log_id) == 0:
        return {idx: row_to_dict(row) for idx, row in enumerate(results)}
    else:
        return row_to_dict(results)
    
def api_health_check():
    with Session() as session:
        results = session.execute(
                text("""
                        SELECT COUNT( DISTINCT id) AS Row_Count
                     FROM log_entry
                    """)).first()
        response = {
            "Status":"All systems good",
            "Log Count":results[0] # pyright: ignore[reportOptionalSubscript]
        }
        return response
    
def api_get_segments():
    """
        Get a straight dump of the segments table for the admin panel.
    """
    with Session() as session:
        results = session.execute(
            text("""
                 SELECT *
                 FROM log_segment
                 """)
        ).fetchall()

    return results

def api_get_enrichments():
    """
        Get a straight dump of the enrichments table for the admin panel.
    """
    with Session() as session:
        results = session.execute(
            text("""
                 SELECT *
                 FROM log_enrichment
                 """)
        ).fetchall()
    return results

def api_delete_log_entry(log_id:int):
    pass

def get_weekly_transcripts(start_date:date, end_date:date):
    """
    Returns the transcripts for a given range.
    """
    transcripts_result = ''
    with Session() as session:
        results = session.execute(
                    text("""
                        SELECT id, entry_date
                        FROM log_entry
                        WHERE entry_date BETWEEN :start_dt AND :end_dt
                        """),
                        {"start_dt": start_date,
                         "end_dt": end_date}
                ).fetchall()
        
        for result in results:
            transcripts_result += f'Entry for {result[1]}:\n'
            transcripts = session.execute(
                text("""
                     SELECT id, log_entry_id, raw_transcript
                     FROM log_segment
                     WHERE log_entry_id = :log_id
                     """),
                     {"log_id": result[0]}
            ).fetchall()
            
            for transcript in transcripts:
                transcripts_result += transcript[2]
            transcripts_result += '\n\n'
    return transcripts_result