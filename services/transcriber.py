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
    import numpy as np

    try:
        audio = ffmpeg.probe(file_path)
    except Exception as e:
        raise ValueError(f"Error occurred while probing audio file: {e}")

    audio_duration = int(float(audio['format']['duration']))

    # Decode audio to a numpy array via ffmpeg pipe so the file handle is
    # released before faster_whisper (CTranslate2) ever touches it.
    # Passing a file path to model.transcribe() causes a Windows file lock
    # (WinError 32) that prevents copying the file afterwards.
    try:
        raw, _ = (
            ffmpeg
            .input(file_path)
            .output('pipe:', format='f32le', acodec='pcm_f32le', ac=1, ar='16000')
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise ValueError(f"Error decoding audio file: {e}")

    audio_array = np.frombuffer(raw, np.float32)

    transcription = ""
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_array, language="en")

    for segment in segments:
        transcription += segment.text + " "

    if not transcription.strip():
        raise ValueError("Transcription is empty. Please check the audio file and transcription process.")
    else:
        print("✅ Transcription completed successfully with length: " + str(len(transcription)) + " characters.")
        print(f"✅ Audio duration: {audio_duration} seconds.")

    return transcription.strip(), audio_duration