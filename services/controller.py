# What do I need to do here:
# 2. Handle the file upload and storage

from services.config import LOGS_DIR, RECORDINGS_DIR, ensure_directories
from services import transcriber, database, llm_client
from datetime import date
import os

def weekly_review(start_date:date, end_date:date) -> str:
    # Gathers the transcripts and returns the LLMs output.
    transcripts = database.get_weekly_transcripts(start_date, end_date)
    summary = llm_client.weekly_review(transcripts)
    return summary

def process_log_entry(audio_path: str, entry_date: str) -> dict:
    ensure_directories() #Make sure the place to save the files exists.
    
    # Step 1 - Transcribe
    transcript, audio_duration = transcriber.transcribe_audio(audio_path)

    # Step 2 - Database: create or get the day's header
    entry_id = database.create_or_get_log_header(entry_date)

    # Step 3 - Database: save segment, get unified transcript
    # TODO - need to sort the proper saving of the file path. Currently it is wrong.
    segment_id = database.create_log_segment(entry_id, audio_path, audio_duration, transcript)
    unified_transcript = database.get_unified_transcripts(entry_id)
    save_uploaded_audio(audio_path, f'{entry_date}-{segment_id}.wav')

    # Step 4 - LLM: format to markdown
    formatted_md = llm_client.llm_formatter(unified_transcript)

    # Step 5 - LLM: generate follow-up questions
    questions = llm_client.llm_question_generator(formatted_md)

    # Step 6 - Database: save enrichment
    database.upsert_log_enrichment(entry_id, formatted_md, questions)

    # Step 7 - Write markdown file
    file_path = LOGS_DIR / f"{entry_date}.md"
    file_path.write_text(formatted_md, encoding="utf-8")

    return {
        "entry_id": entry_id,
        "transcript": unified_transcript,
        "formatted_md": formatted_md,
        "questions": questions
    }

def save_uploaded_audio(audio_file, file_name:str) -> str:
    # This will allow the user to upload audio to the UI and it will be saved in the right place with the right name.
    # Returns True if successful
    import shutil

    DESTINATION_PATH = os.path.join(RECORDINGS_DIR, file_name)

    try:
        # This line does the actual work: copying and renaming
        shutil.copy2(audio_file, DESTINATION_PATH)
        
        print("-" * 40)
        print(f"✅ Success! File copied and renamed.")
        print(f"   Source: {audio_file}")
        print(f"   Destination: {DESTINATION_PATH}")

    except FileNotFoundError:
        print("❌ Error: Source file not found. Please check the SOURCE_PATH.")
    except FileExistsError:
        # This case handles if the destination path is a directory itself, 
        # or if the destination file already exists and we aren't careful.
        print(f"⚠️ Warning: Could not copy. The destination path might already exist.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

    return DESTINATION_PATH

def transcribe_audio(audio_file) -> str:
    # This will transcribe some given audio and return the string.
    return 'Not Implemented'
