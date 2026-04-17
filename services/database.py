import sqlite3
sqlite_db_path = '../db/application.db'

def reset_db():
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    delete_log_header_query = "DELETE FROM log_entry;"
    delete_log_segments_query = "DELETE FROM log_segment;"
    delete_log_enrichment_query = "DELETE FROM log_enrichment;"

    try:
        cursor.execute(delete_log_header_query)
        cursor.execute(delete_log_segments_query)
        cursor.execute(delete_log_enrichment_query)
        conn.commit()
        print("✅ Database reset successfully.")
    except sqlite3.Error as e:
        print(f"❌ An error occurred: {e}")
    finally:
        conn.close()
    

def create_log_header():
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    Insert_log_entry_query = """
    INSERT INTO log_entry (entry_date, created_at, updated_at)
    VALUES ('2024-06-02', datetime('now'), datetime('now'));
    """
    try:
        cursor.execute(Insert_log_entry_query)
        new_record_id = cursor.lastrowid
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ An error occurred: {e}")
        new_record_id = None
    finally:
        conn.close()

        if new_record_id == None:
            raise ValueError("Failed to create log entry header. Aborting process.")
        else:
            print(f"✅ Log entry header created with ID: {new_record_id}")

    return new_record_id

def create_log_segment(log_entry_id, audio_filename, duration_secs, raw_transcript):
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    Insert_log_entry_query = """
    INSERT INTO log_segment (log_entry_id, audio_filename, duration_secs, raw_transcript, created_at)
    VALUES (?, ?, ?, ?, datetime('now'));
    """
    try:
        cursor.execute(Insert_log_entry_query, (log_entry_id, audio_filename, duration_secs, raw_transcript))
        new_record_id = cursor.lastrowid
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ An error occurred: {e}")
        new_record_id = None
    finally:
        conn.close()

    if new_record_id == None:
        raise ValueError("Failed to create log segment. Aborting process.")
    else:
        print(f"✅ Log segment created with ID: {new_record_id}")

    return new_record_id

def create_log_enrichment(log_entry_id, formatted_md, followup_qs):
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    Insert_log_entry_query = """
    INSERT INTO log_enrichment (log_entry_id, formatted_md, followup_qs, generated_at)
    VALUES (?, ?, ?, datetime('now'));
    """
    try:
        cursor.execute(Insert_log_entry_query, (log_entry_id, formatted_md, followup_qs))
        new_record_id = cursor.lastrowid
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ An error occurred: {e}")
        new_record_id = None
    finally:
        conn.close()
        
    return new_record_id