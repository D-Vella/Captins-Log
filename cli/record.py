"""
record.py - Script to query and list available audio devices.
Used for audio recording in the Captain's Log project.
"""

import sounddevice as sd
import json
import scipy.io.wavfile as wav_file
import soundfile as sf

def list_audio_devices():
    """Prints a list of available audio input/output devices."""
    try:
        devices = sd.query_devices()
        print("Available input audio devices:")
        input_devices = [device for device in devices if device['max_input_channels'] > 0]
        for device in input_devices:
            name = device['name']
            device_id = device['index']
            print(f"ID: {device_id}, Name: {name}")
    except Exception as e:
        print(f"Error querying devices: {e}")

def record_audio(duration, sample_rate=44100, file_name=None):
    """Records audio from the specified device for a given duration.
    Args:
        duration (int): The duration of the recording in seconds.
        sample_rate (int, optional): The sample rate for the recording. Defaults to 44100.
        file_name (str, optional): The name of the file to save the recording to. Defaults to None.

    Returns:
        numpy.ndarray: The recorded audio data.
    """
    if file_name is None:
        raise ValueError("file_name must be provided to save the recording.")
    
    if '.' in file_name:
        raise ValueError("file_name should not contain an extension. The function will save the file as a .wav by default.")

    try:
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()
    except Exception as e:
        raise ValueError(f"Error recording audio: {e}")
    
        
    # Save the recording to a file
    sf.write(f"{file_name}.wav", audio_data, sample_rate)
    return f"{file_name}.wav"


if __name__ == "__main__":
    list_audio_devices()