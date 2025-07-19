import torch
import os
import traceback
from transformers import WhisperForConditionalGeneration, WhisperProcessor
import librosa
import re

# This dictionary will hold the loaded model and processor
LOADED_WHISPER_ASSETS = {}

# The path to the directory containing your fine-tuned model checkpoint
WHISPER_MODEL_PATH = "./models/checkpoint-100"

def _load_whisper_model_and_processor(model_path: str):
    """
    Loads a fine-tuned Whisper model and its processor from a local directory
    using the Hugging Face transformers library.
    Handles GPU placement if available.
    """
    if "model" in LOADED_WHISPER_ASSETS and "processor" in LOADED_WHISPER_ASSETS:
        print(f"Whisper model and processor from '{model_path}' already loaded.")
        return LOADED_WHISPER_ASSETS["model"], LOADED_WHISPER_ASSETS["processor"]

    try:
        print(f"Attempting to load Whisper model and processor from: {model_path}")

        # Check if the directory and essential files exist
        if not os.path.isdir(model_path):
            print(f"ERROR: Model directory not found at {model_path}")
            return None, None
        
        required_files = ["config.json", "model.safetensors"]
        for f in required_files:
            if not os.path.exists(os.path.join(model_path, f)):
                print(f"ERROR: Missing required model file: {f} in {model_path}")
                return None, None

        # Load the processor - processor files might be missing so use the base model
        try:
            processor = WhisperProcessor.from_pretrained(model_path)
        except Exception as e:
            print(f"Could not load processor from '{model_path}': {e}")
            print(f"Falling back to 'openai/whisper-small'.")
            processor = WhisperProcessor.from_pretrained("openai/whisper-small")

        # Load the model
        model = WhisperForConditionalGeneration.from_pretrained(model_path)

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model.to(device)
        print(f"Whisper model from '{model_path}' moved to {device}.")

        LOADED_WHISPER_ASSETS["model"] = model
        LOADED_WHISPER_ASSETS["processor"] = processor
        print(f"Successfully loaded Whisper model and processor from: {model_path}")
        return model, processor
    except Exception as e:
        print(f"ERROR: Failed to load Whisper model/processor from '{model_path}': {e}")
        print(traceback.format_exc())
        return None, None

def detect_script(text):
    """
    Detects whether the given text is primarily in Bengali or Latin script.
    Returns 'bengali', 'sylheti', or 'english' based on character frequency.
    
    Note: This function treats Sylheti as Bengali script for detection purposes.
    """
    # Remove the Unicode replacement character (U+FFFD)
    text = text.replace('\ufffd', '')
    
    # Count Bengali vs Latin characters
    bengali_count = len(re.findall(r'[\u0980-\u09FF]', text))
    latin_count = len(re.findall(r'[a-zA-Z]', text))
    
    # Log detailed character analysis for debugging
    print(f"--- Script detection: Text='{text}', Bengali chars={bengali_count}, Latin chars={latin_count} ---")
    
    # Log sample characters from each script that were found
    bengali_chars = re.findall(r'[\u0980-\u09FF]', text)
    latin_chars = re.findall(r'[a-zA-Z]', text)
    
    if bengali_chars:
        print(f"--- Bengali script characters found: {bengali_chars[:10]} ---")
    if latin_chars:
        print(f"--- Latin script characters found: {latin_chars[:10]} ---")
    
    # If most characters are Bengali script
    if bengali_count > latin_count:
        return 'sylheti'  # Default to sylheti when Bengali script is detected
    else:
        return 'english'

def clean_transcript(text):
    """
    Cleans up transcription artifacts.
    """
    # Remove the Unicode replacement character (U+FFFD)
    text = text.replace('\ufffd', '')
    # Remove any other common artifacts
    text = text.strip()
    return text

def transcribe_audio(audio_path: str, source_language: str = None) -> dict:
    """
    Transcribes an audio file using the fine-tuned Whisper model.

    Args:
        audio_path (str): The path to the audio file to transcribe.
        source_language (str, optional): The source language hint.

    Returns:
        dict: A dictionary with 'text' (transcribed text) and 'detected_language'
              (what language was detected based on script analysis).
    """
    print(f"--- Attempting audio transcription for: {audio_path} ---")

    if not os.path.exists(audio_path):
        return {"text": f"Error: Audio file not found at {audio_path}", "detected_language": None}

    if os.path.getsize(audio_path) < 1024:
        print(f"--- WARNING: Audio file at {audio_path} is very small ({os.path.getsize(audio_path)} bytes). This may indicate an empty or problematic recording. ---")
        return {"text": "Error: Recorded audio is too short or empty. Please speak for a moment.", "detected_language": None}

    model, processor = _load_whisper_model_and_processor(WHISPER_MODEL_PATH)
    if model is None or processor is None:
        return {"text": f"Error: Whisper model from '{WHISPER_MODEL_PATH}' could not be loaded for transcription.", "detected_language": None}

    try:
        # Load and process the audio file
        audio_input, sampling_rate = librosa.load(audio_path, sr=16000)

        # Process the audio to create input features
        input_features = processor(audio_input, sampling_rate=sampling_rate, return_tensors="pt").input_features
        
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        input_features = input_features.to(device)

        # If source_language was provided, use it as a hint; otherwise default to Bengali
        lang_code = "bn"  # Default to Bengali/Sylheti
        if source_language == "english":
            lang_code = "en"
            
        # Generate token IDs
        forced_decoder_ids = processor.get_decoder_prompt_ids(language=lang_code, task="transcribe")
        predicted_ids = model.generate(input_features, forced_decoder_ids=forced_decoder_ids)

        # Decode the token IDs to text
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        
        # Clean up the transcript (remove artifacts)
        cleaned_transcription = clean_transcript(transcription)
        
        # Detect the script to determine the actual language
        detected_language = detect_script(cleaned_transcription)
        
        print(f"--- Transcription successful: '{cleaned_transcription}' (Detected language: {detected_language}) ---")
        return {
            "text": cleaned_transcription,
            "detected_language": detected_language
        }
    except Exception as e:
        print(f"--- ERROR during Whisper transcription of {audio_path}: {e} ---")
        print(traceback.format_exc())
        return {
            "text": f"Error: Failed to transcribe audio file. {type(e).__name__}: {str(e)}",
            "detected_language": None
        }

# Ensure the model is loaded when this module is imported
if __name__ != '__main__':
    _load_whisper_model_and_processor(WHISPER_MODEL_PATH)
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