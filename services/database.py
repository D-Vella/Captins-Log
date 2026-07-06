from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, date
from services.config import DATABASE_PATH, POSTGRES_CONFIG
import psycopg2

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def check_connection(db_type: str) -> str:
    """
    Checks the connection to the specified database type.
    Args:
        db_type (str): The type of database to check. Valid values are "sqlite" and "postgres".
    Returns:
        str: "OK" if the connection is successful, an error message otherwise.
    """
    try:
        if db_type == "sqlite":
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        elif db_type == "postgres":
            connection = psycopg2.connect(
                dbname=POSTGRES_CONFIG["dbname"],
                user=POSTGRES_CONFIG["user"],
                password=POSTGRES_CONFIG["password"],
                host=POSTGRES_CONFIG["host"],
                port=POSTGRES_CONFIG["port"]
            )
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            connection.close()
        else:
            return "Invalid database type. Use 'sqlite' or 'postgres'."
        return "OK"
    except Exception as e:
        return(f"Connection check failed for {db_type}: {e}")

def reset_db():
    """
    Resets the database by deleting all records from log_enrichment, log_segment, and log_entry tables.
    This function is idempotent and will not raise an error if tables are empty.
    """
    with Session() as session:
        session.execute(text("DELETE FROM log_enrichment;"))
        session.execute(text("DELETE FROM log_segment;"))
        session.execute(text("DELETE FROM log_entry;"))
        session.commit()
    print("✅ Database reset successfully.")

def create_or_get_log_header(entry_date: str) -> int:
    """
    Creates or retrieves a log entry header based on the provided entry date.
    If a log entry with the given date exists, returns its ID. Otherwise, creates a new entry and returns the new ID.
    Args:
        entry_date (str): The date of the log entry in string format.
    Returns:
        int: The ID of the log entry.
    """
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

def create_log_segment(log_entry_id: int, audio_filename: str, audio_duration: float, raw_transcript: str) -> int:
    """
    Creates a new log segment associated with a log entry.
    Args:
        log_entry_id (int): The ID of the log entry this segment belongs to.
        audio_filename (str): The filename of the audio file associated with this segment.
        audio_duration (float): The duration of the audio segment in seconds.
        raw_transcript (str): The raw transcript text of the audio segment.
    Returns:
        int: The ID of the newly created log segment row.
    """
    with Session() as session:
        session.execute(
            text("""INSERT INTO log_segment (log_entry_id, audio_filename, audio_duration, raw_transcript, created_at, updated_at)
                    VALUES (:entry_id, :filename, :audio_duration, :transcript, :now, :now)"""),
            {"entry_id": log_entry_id, "filename": audio_filename,
             "audio_duration": audio_duration, "transcript": raw_transcript,
             "now": datetime.now(timezone.utc)}
        )
        session.commit()
        segment_id = session.execute(text("SELECT last_insert_rowid()")).scalar()
        print(f"✅ Log segment created for entry ID: {log_entry_id}")
        return segment_id

def create_log_enrichment(log_entry_id: int, formatted_md: str, followup_qs: str) -> None:
    """
    Creates a new log enrichment entry in the log_enrichment table.
    Args:
        log_entry_id (int): The ID of the log entry this enrichment belongs to.
        formatted_md (str): The formatted Markdown content of the enrichment.
        followup_qs (str): The follow-up questions associated with the enrichment.
    """
    with Session() as session:
        session.execute(
            text("""INSERT INTO log_enrichment (log_entry_id, formatted_md, followup_qs, created_at, updated_at)
                    VALUES (:entry_id, :md, :qs, :now, :now)"""),
            {"entry_id": log_entry_id, "md": formatted_md,
             "qs": followup_qs, "now": datetime.now(timezone.utc)}
        )
        session.commit()

def update_log_enrichment(log_entry_id: int, formatted_md: str, followup_qs: str) -> None:
    """
    Updates an existing log enrichment entry in the log_enrichment table.
    Args:
        log_entry_id (int): The ID of the log entry to update.
        formatted_md (str): The new formatted Markdown content for the enrichment.
        followup_qs (str): The new follow-up questions for the enrichment.
    """
    with Session() as session:
        session.execute(
            text("""UPDATE log_enrichment 
                    SET formatted_md = :md, 
                        followup_qs = :qs, 
                        updated_at = :now
                    WHERE log_entry_id = :entry_id
                 """),
            {"entry_id": log_entry_id, "md": formatted_md,
             "qs": followup_qs, "now": datetime.now(timezone.utc)}
        )
        session.commit()

def upsert_log_enrichment(log_entry_id: int, formatted_md: str, followup_qs: str) -> None:
    """
    Inserts a new log enrichment entry or updates an existing one if it already exists.
    This is an upsert operation (insert + update) based on whether the log_entry_id exists.
    Args:
        log_entry_id (int): The ID of the log entry to upsert.
        formatted_md (str): The formatted Markdown content for the enrichment.
        followup_qs (str): The follow-up questions for the enrichment.
    """
    #check if entry already exists
    with Session() as session:
        existing_count = session.execute(
            text("""
                 SELECT count(log_entry_id)
                 FROM log_enrichment
                 WHERE log_entry_id = :log_id
                 """),
                 {"log_id":log_entry_id}
        ).fetchone()

    if not existing_count or existing_count[0] == 0:
        create_log_enrichment(log_entry_id, formatted_md, followup_qs)
    else:
        update_log_enrichment(log_entry_id, formatted_md, followup_qs)


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
    """
    Checks the health of the database by counting the number of distinct log entries.
    Returns a response dictionary with system status and log count.
    Returns:
        dict: A dictionary containing:
            - "Status": A string indicating system status (e.g., "All systems good")
            - "Log Count": The number of distinct log entries in the log_entry table
    """
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
    """
    Deletes a log entry from the log_entry table based on the provided log ID.
    Args:
        log_id (int): The ID of the log entry to be deleted.
    """
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
            transcripts_result += get_unified_transcripts(log_id=result[0])
            transcripts_result += '\n\n'
    return transcripts_result

def get_unified_transcripts(log_id:int) -> str:
    """
    Concatenates raw transcripts from all log segments associated with a log entry.
    Args:
        log_id (int): The ID of the log entry to retrieve transcripts for.
    Returns:
        str: A concatenated string of all raw transcripts, separated by newlines.
    """
    transcripts_result = ''
    with Session() as session:
        transcripts = session.execute(
                text("""
                     SELECT id, log_entry_id, raw_transcript
                     FROM log_segment
                     WHERE log_entry_id = :log_id
                     """),
                     {"log_id": log_id}
            ).fetchall()
            
    for transcript in transcripts:
        transcripts_result += transcript[2]
    transcripts_result += '\n\n'

    return transcripts_result

def get_dated_entry_id(entry_date: str) -> int:
    """
    Gets the log entry id for a given date, if it exists.
    """
    with Session() as session:
        result = session.execute(
            text("""
                 SELECT id
                 FROM log_entry
                 WHERE entry_date = :entry_date
                 """),
            {"entry_date": entry_date}
        ).fetchone()
        result_int = int(result[0]) if result else None
    return result_int # type: ignore

def search_logs_by_keyword(keyword: str):
    """
    Searches for logs that contain the specified keyword in their raw transcripts.
    Args:
        keyword (str): The keyword to search for within the raw transcripts of log segments.
    Returns:
        list: A list of log entries (dictionaries) that contain the keyword in their transcripts.
    """
    matching_entries = []
    with Session() as session:
        results = session.execute(
            text("""
                 SELECT le.id, le.entry_date, ls.raw_transcript, lech.formatted_md
                 FROM log_entry le
                    JOIN log_segment ls ON le.id = ls.log_entry_id
                    JOIN log_enrichment lech ON le.id = lech.log_entry_id
                 WHERE ls.raw_transcript LIKE :keyword or lech.formatted_md LIKE :keyword
                 """),
            {"keyword": f"%{keyword.upper()}%"}
        ).fetchall()

    for result in results:
        entry_dict = {
            "id": result[0],
            "entry_date": result[1],
            "raw_transcript": result[2],
            "formatted_md": result[3]
        }
        matching_entries.append(entry_dict)

    return matching_entries