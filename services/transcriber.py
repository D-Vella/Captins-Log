from pathlib import Path

import httpx

from services.config import WHISPER_SERVER_URL


def transcribe_audio(file_path) -> tuple[str, int]:
    """Transcribes an audio file into text using a remote whisper.cpp server.

    Args:
        file_path (str): Path to the audio file to be transcribed.

    Returns:
        tuple[str, int]: A tuple containing the transcribed text and the duration of the audio in seconds.

    Raises:
        ValueError: If there's an error probing the audio file, contacting the whisper.cpp server, or if the transcription is empty.
    """
    import ffmpeg
    try:
        audio = ffmpeg.probe(file_path)
    except Exception as e:
        raise ValueError(f"Error occurred while probing audio file: {e}")

    audio_duration = int(float(audio['format']['duration']))

    try:
        with open(file_path, "rb") as f:
            response = httpx.post(
                f"{WHISPER_SERVER_URL}/inference",
                files={"file": (Path(file_path).name, f, "application/octet-stream")},
                data={"response_format": "json"},
                timeout=300,
            )
        response.raise_for_status()
    except Exception as e:
        raise ValueError(f"Error occurred while contacting whisper.cpp server: {e}")

    transcription = response.json().get("text", "").strip()

    if not transcription:
        raise ValueError("Transcription is empty. Please check the audio file and transcription process.")
    else:
        print("✅ Transcription completed successfully with length: " + str(len(transcription)) + " characters.")
        print(f"✅ Audio duration: {audio_duration} seconds.")

    return transcription, audio_duration


def check_connection() -> str:
    """Checks the connectivity to the whisper.cpp server.

    Returns:
        str: A string indicating the status of the connection.
    """
    try:
        response = httpx.get(f"{WHISPER_SERVER_URL}/health", timeout=5)
        response.raise_for_status()
        return "Whisper server is reachable."
    except Exception as e:
        return f"Failed to reach Whisper server: {e}"