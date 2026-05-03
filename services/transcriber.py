def transcribe_audio(file_path) -> tuple[str, int]:
    """Transcribes an audio file into text.

    Args:
        file_path (str): Path to the audio file to be transcribed.

    Returns:
        tuple[str, int]: A tuple containing the transcribed text and the duration of the audio in seconds.

    Raises:
        ValueError: If there's an error probing the audio file or if the transcription is empty.
    """
    from faster_whisper import WhisperModel
    import ffmpeg
    try:
        audio = ffmpeg.probe(file_path)
    except Exception as e:
        raise ValueError(f"Error occurred while probing audio file: {e}")

    audio_duration = int(float(audio['format']['duration']))

    transcription = ""
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(file_path)

    for segment in segments:
        transcription += segment.text + " "

    if not transcription.strip():
        raise ValueError("Transcription is empty. Please check the audio file and transcription process.")
    else:
        print("✅ Transcription completed successfully with length: " + str(len(transcription)) + " characters.")
        print(f"✅ Audio duration: {audio_duration} seconds.")

    return transcription.strip(), audio_duration