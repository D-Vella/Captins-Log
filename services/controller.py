# What do I need to do here:
# 2. Handle the file upload and storage

from services.config import LOGS_DIR, RECORDINGS_DIR
from services import transcriber, database, llm_client
from datetime import date

def weekly_review(start_date:date, end_date:date) -> str:
    # Gathers the transcripts and returns the LLMs output.
    transcripts = database.get_weekly_transcripts(start_date, end_date)
    summary = llm_client.weekly_review(transcripts)
    return summary

def process_log_entry(audio_path: str, entry_date: str) -> dict:
    
    # Step 1 - Transcribe
    transcript, audio_duration = transcriber.transcribe_audio(audio_path)

    # Step 2 - Database: create or get the day's header
    entry_id = database.create_or_get_log_header(entry_date)

    # Step 3 - Database: save segment, get unified transcript
    database.create_log_segment(entry_id, audio_path, audio_duration, transcript)
    unified_transcript = database.get_unified_transcripts(entry_id)

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

def save_uploaded_audio(audio_file, create_entry=False, entry_date=None) -> bool:
    # This will allow the user to upload audio to the UI and it will be saved in the right place with the right name.
    # Returns True if successful

    return False

def transcribe_audio(audio_file) -> str:
    # This will transcribe some given audio and return the string.
    return 'Not Implemented'
