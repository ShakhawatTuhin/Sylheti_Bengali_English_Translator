import torch
import whisper
import os
import traceback

# This dictionary will hold loaded Whisper models to avoid reloading them
LOADED_WHISPER_MODELS = {}

# You can specify different Whisper models here.
# For initial testing, 'base' or 'small' are good starting points for performance.
# For better accuracy, 'medium' or 'large' might be considered later, but they are larger.
# If you fine-tune, you'd put your fine-tuned model path/name here.
WHISPER_MODEL_NAME = "medium" # Or "small", "medium", "large" as needed

def _load_whisper_model(model_name: str):
    """
    Loads a Whisper model (and downloads it if not available locally).
    Handles GPU placement if available.
    """
    if model_name in LOADED_WHISPER_MODELS:
        print(f"Whisper model '{model_name}' already loaded.")
        return LOADED_WHISPER_MODELS[model_name]

    try:
        print(f"Attempting to load Whisper model: {model_name}")
        model = whisper.load_model(model_name)

        if torch.cuda.is_available():
            model.to('cuda')
            print(f"Whisper model '{model_name}' moved to GPU.")
        else:
            print(f"GPU not available, Whisper model '{model_name}' using CPU.")

        LOADED_WHISPER_MODELS[model_name] = model
        print(f"Successfully loaded Whisper model: {model_name}")
        return model
    except Exception as e:
        print(f"ERROR: Failed to load Whisper model '{model_name}': {e}")
        print(traceback.format_exc())
        return None

def transcribe_audio(audio_path: str, source_language: str) -> str:
    """
    Transcribes an audio file using the loaded Whisper model.

    Args:
        audio_path (str): The path to the audio file to transcribe.
        source_language (str): The source language of the audio file.

    Returns:
        str: The transcribed text, or an error message.
    """
    print(f"--- Attempting audio transcription for: {audio_path} ---")

    if not os.path.exists(audio_path):
        return f"Error: Audio file not found at {audio_path}"
    
    # Check if the audio file is empty or too small (e.g., less than 1KB)
    if os.path.getsize(audio_path) < 1024: # 1KB threshold
        print(f"--- WARNING: Audio file at {audio_path} is very small ({os.path.getsize(audio_path)} bytes). This may indicate an empty or problematic recording. ---")
        return "Error: Recorded audio is too short or empty. Please speak for a moment."

    model = _load_whisper_model(WHISPER_MODEL_NAME)
    if model is None:
        return f"Error: Whisper model '{WHISPER_MODEL_NAME}' could not be loaded for transcription."

    try:
        # Determine language code and prompt for Whisper based on the source language
        whisper_lang_code = "en"  # Default to English
        sylheti_prompt = ""  # Default to no prompt

        if source_language in ["sylheti", "bengali"]:
            whisper_lang_code = "bn"
            sylheti_prompt = "মুই ভাত খাই। তুমার নাম কিতা? আমি এখন যাইরাম।"

        print(f"--- Transcribing with language hint: '{whisper_lang_code}' ---")

        # Whisper automatically handles many audio formats
        result = model.transcribe(
            audio_path,
            fp16=torch.cuda.is_available(),
            language=whisper_lang_code,
            initial_prompt=sylheti_prompt
        )
        transcription = result["text"]
        
        # Safely print language probability if available
        if 'language' in result and 'language_probability' in result:
            print(f"--- Whisper detected language: {result['language']} (probability: {result['language_probability']:.2f}) ---")
        else:
            print("--- Whisper language detection information not available. ---")

        print(f"--- Transcription successful: '{transcription}' ---")
        return transcription
    except Exception as e:
        print(f"--- ERROR during Whisper transcription of {audio_path}: {e} ---")
        print(traceback.format_exc())
        return f"Error: Failed to transcribe audio file. {type(e).__name__}: {str(e)}"

# Ensure the model is loaded when this module is imported
if __name__ != '__main__':
    _load_whisper_model(WHISPER_MODEL_NAME)
else:
    print("Running speech_recognizer.py directly (for testing purposes only).")
    # Example usage for direct testing:
    # You would need an actual audio file for this to work.
    # test_audio_path = "path/to/your/test_audio.wav"
    # if os.path.exists(test_audio_path):
    #     print(f"Testing transcription for {test_audio_path}")
    #     transcribed_text = transcribe_audio(test_audio_path)
    #     print(f"Transcription result: {transcribed_text}")
    # else:
    #     print(f"Test audio file not found at {test_audio_path}. Skipping direct test.") 