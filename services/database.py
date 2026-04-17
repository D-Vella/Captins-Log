import sqlite3
sqlite_db_path = '../db/application.db'

def run_query(query, params=(), commit=False, fetch='none'):
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
        if fetch == 'one':
            return cursor.fetchone()
        elif fetch == 'all':
            return cursor.fetchall()
        elif fetch == 'id':
            return cursor.lastrowid
        else:
            return None
    except sqlite3.Error as e:
        print(f"❌ An error occurred: {e}")
        return None
    finally:
        conn.close()

def reset_db():
    delete_log_header_query = "DELETE FROM log_entry;"
    delete_log_segments_query = "DELETE FROM log_segment;"
    delete_log_enrichment_query = "DELETE FROM log_enrichment;"

    run_query(delete_log_header_query, commit=True)
    run_query(delete_log_segments_query, commit=True)
    run_query(delete_log_enrichment_query, commit=True)
    print("✅ Database reset successfully.")
    

def create_or_get_log_header(entry_date: str):
    Get_log_entry_query = """
    SELECT id FROM log_entry WHERE entry_date = ?;
    """
    result = run_query(Get_log_entry_query, (entry_date,), fetch='one')

    if result:
        log_entry_id = result[0] # pyright: ignore[reportIndexIssue]
    else:
        Insert_log_entry_query = """
        INSERT INTO log_entry (entry_date, created_at, updated_at)
        VALUES (?, datetime('now'), datetime('now'));
        """
        log_entry_id = run_query(Insert_log_entry_query, (entry_date,), commit=True, fetch='id')

    return log_entry_id

def create_log_segment(log_entry_id, audio_filename, duration_secs, raw_transcript) -> str:
    """Creates a log segment record in the database linked to the provided log entry ID. If there are multiple segements for a given log entry, the funtion will return a unified transcript for all segments linked to that log entry.
    Args:
        log_entry_id (int): The ID of the log entry to link this segment to.
        audio_filename (str): The filename of the audio recording.
        duration_secs (float): The duration of the audio recording in seconds.
        raw_transcript (str): The raw transcript text from the audio.
        Returns:
            str: The unified transcript for all segments linked to the log entry.
    """
    result = []
    Insert_log_entry_query = """
    INSERT INTO log_segment (log_entry_id, audio_filename, duration_secs, raw_transcript, created_at)
    VALUES (?, ?, ?, ?, datetime('now'));
    """
    new_record_id = run_query(Insert_log_entry_query, (log_entry_id, audio_filename, duration_secs, raw_transcript), commit=True, fetch='id')

    if new_record_id is None:
        raise ValueError("Failed to create log segment. Aborting process.")
    else:
        print(f"✅ Log segment created with ID: {new_record_id}")

    # Check if there are multiple segments for the same log entry and unify their transcripts if so

    get_unified_transcript_query = """
        SELECT GROUP_CONCAT(raw_transcript, ' ') AS unified_transcript
        FROM log_segment 
        WHERE log_entry_id = ?;
    """
    result = run_query(get_unified_transcript_query, (log_entry_id,), fetch='one')
    unified_transcript = result[0] if result else raw_transcript # pyright: ignore[reportIndexIssue]

    return unified_transcript

def create_log_enrichment(log_entry_id, formatted_md, followup_qs):
    Insert_log_entry_query = """
    INSERT INTO log_enrichment (log_entry_id, formatted_md, followup_qs, generated_at)
    VALUES (?, ?, ?, datetime('now'));
    """
    new_record_id = run_query(Insert_log_entry_query, (log_entry_id, formatted_md, followup_qs), commit=True, fetch='id')
        
    return new_record_id