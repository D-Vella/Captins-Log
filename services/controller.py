# What do I need to do here:
# 2. Handle the file upload and storage

from services.config import LOGS_DIR, RECORDINGS_DIR, ensure_directories
from services import transcriber, database, llm_client
from datetime import date
import os
import shutil

def get_weekly_reviews() -> dict:
    # This will return a dict of all the weekly reviews that have been generated, with the key as the week range and the value as the summary.
    reviews = {}
    for file in os.listdir(LOGS_DIR):
        if file.startswith("Review") and file.endswith(".md"):
            week_range = file[len("Review "):-len(".md")]
            reviews[week_range] = (LOGS_DIR / file).read_text(encoding="utf-8")
    return reviews

def weekly_review(start_date:date, end_date:date) -> str:
    # Gathers the transcripts and returns the LLMs output.
    transcripts = database.get_weekly_transcripts(start_date, end_date)
    summary = llm_client.weekly_review(transcripts)
    entry_week = f"Review {start_date.isoformat()} to {end_date.isoformat()}"
    file_path = LOGS_DIR / f"{entry_week}.md"
    file_path.write_text(summary, encoding="utf-8")

    return summary

def process_log_entry(audio_path: str, entry_date: str) -> dict:
    ensure_directories() #Make sure the place to save the files exists.
    
    # Step 1 - Transcribe
    transcript, audio_duration = transcriber.transcribe_audio(audio_path)

    # Step 2 - Database: create or get the day's header
    entry_id = database.create_or_get_log_header(entry_date)

    # Step 3 - Database: save segment, get unified transcript
    segment_id = database.create_log_segment(entry_id, audio_path, audio_duration, transcript)
    unified_transcript = database.get_unified_transcripts(entry_id)
    save_uploaded_audio(audio_path, f'{entry_date}-{segment_id}.wav')

    # Step 4 - LLM: format to markdown
    formatted_md = llm_client.llm_formatter(unified_transcript)

    # Step 5 - LLM: generate follow-up questions
    questions = llm_client.llm_question_generator(formatted_md)

    # Step 6 - Database: save enrichment
    database.upsert_log_enrichment(entry_id, formatted_md, questions)

    md_file_contents = f"# Diary Entry for {entry_date}\n\n"
    md_file_contents += formatted_md
    md_file_contents += "\n\n---\n\n"
    md_file_contents += "## Follow-up Questions\n\n"
    md_file_contents += questions

    # Step 7 - Write markdown file
    file_path = LOGS_DIR / f"{entry_date}.md"
    file_path.write_text(md_file_contents, encoding="utf-8")

    return {
        "entry_id": entry_id,
        "transcript": unified_transcript,
        "formatted_md": formatted_md,
        "questions": questions
    }

def save_uploaded_audio(audio_file: str, file_name: str) -> str:
    destination = os.path.join(RECORDINGS_DIR, file_name)

    abs_source = os.path.normcase(os.path.abspath(audio_file))
    abs_dest = os.path.normcase(os.path.abspath(destination))
    recordings_norm = os.path.normcase(os.path.abspath(str(RECORDINGS_DIR)))

    # File is already in the recordings folder — nothing to copy or delete.
    # This happens during rebuild_database() where the source IS the recording.
    if abs_source == abs_dest or abs_source.startswith(recordings_norm + os.sep):
        return audio_file

    try:
        shutil.copy2(audio_file, destination)
        print("-" * 40)
        print(f"✅ Audio saved to recordings.")
        print(f"   Source:      {audio_file}")
        print(f"   Destination: {destination}")
    except FileNotFoundError:
        print("❌ Error: Source file not found.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

    return destination

def transcribe_audio(audio_file) -> str:
    # This will transcribe some given audio and return the string.
    return 'Not Implemented'

def rebuild_database(on_progress=None):
    # This will clear the database and reprocess all the log files in the source directory.
    # Use with caution!

    # Clear the database
    database.reset_db()

    # Clear the markdown files (they will be remade).
    for file in os.listdir(LOGS_DIR):
        if file.endswith('.md'):
            os.unlink(os.path.join(LOGS_DIR, file))  # Delete the markdown files to avoid orphaned files

    wav_files = sorted([f for f in os.listdir(RECORDINGS_DIR) if f.endswith('.wav')])
    total = len(wav_files)

    for i, file in enumerate(wav_files):
        if on_progress:
            on_progress(i, total, file)
        audio_path = os.path.join(RECORDINGS_DIR, file)
        entry_date = file[:10]  # Assuming filename format is "YYYY-MM-DD-segmentID.wav"
        process_log_entry(audio_path, entry_date)

    if on_progress:
        on_progress(total, total, "Done")
