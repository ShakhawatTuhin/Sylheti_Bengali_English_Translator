# scripts/translator.py

import os
import traceback
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

LOADED_MODELS = {}

# ===>>> NEW MODEL_PATHS using Hugging Face Hub identifiers <<<===
HF_USERNAME = "ShakhawatTuhin" # Replace with your actual HF username

MODEL_PATHS = {
    ("sylheti", "bengali"): f"{HF_USERNAME}/sylheti_translator_sy_bn_1396", # Default best Sy->Bn
    # ("sylheti", "bengali", "899"): f"{HF_USERNAME}/sylheti_translator_sy_bn_899", # For specific selection if needed

    ("sylheti", "english"): f"{HF_USERNAME}/sylheti_translator_sy_en_1396", # Default best Sy->En
    # ("sylheti", "english", "899"): f"{HF_USERNAME}/sylheti_translator_sy_en_899", # For specific selection

    # Add Bn->Sy, En->Sy if you train and upload them
    # ("bengali", "sylheti"): f"{HF_USERNAME}/sylheti-translator-bn-sy-XXXX",
    # ("english", "sylheti"): f"{HF_USERNAME}/sylheti-translator-en-sy-XXXX",
}
# =================================================================

def _load_model_and_tokenizer(model_identifier):
    """
    Loads a single model and tokenizer FROM HUGGING FACE HUB IDENTIFIER.
    Handles GPU placement if available.
    """
    try:
        print(f"Attempting to load model from Hugging Face Hub: {model_identifier}")
        # AutoTokenizer and AutoModelForSeq2SeqLM will automatically download
        # from the Hub if the identifier is valid and public (or you're logged in for private).
        tokenizer = AutoTokenizer.from_pretrained(model_identifier)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_identifier)
        model.eval()

        if torch.cuda.is_available():
            model.to('cuda')
            print(f"Model '{model_identifier}' moved to GPU.")
        else:
            print(f"GPU not available, Model '{model_identifier}' using CPU.")

        print(f"Successfully loaded: '{model_identifier}' from Hugging Face Hub.")
        return model, tokenizer

    except Exception as e:
        print(f"ERROR: Failed to load model/tokenizer from Hugging Face Hub '{model_identifier}': {e}")
        print(traceback.format_exc())
        return None, None

# ... (rest of your translator.py, load_all_models and translate function remain largely the same) ...
# The _load_model_and_tokenizer function is the main part that changes.
# The check for local paths in _load_model_and_tokenizer can be removed.

# --- Helper Function to Load a Single Model ---
def _load_model_and_tokenizer(model_identifier):
    """
    Loads a single model and tokenizer from a local path or Hugging Face Hub identifier.
    Handles GPU placement if available.
    """
    try:
        # Check if it's potentially a local path relative to this script
        is_local_path = model_identifier.startswith("../") or os.path.exists(model_identifier)

        model_path_or_name = model_identifier
        if is_local_path:
            # Build the absolute path if it's relative
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            model_path_or_name = os.path.abspath(os.path.join(current_script_dir, model_identifier))
            print(f"Attempting to load local model from resolved path: {model_path_or_name}")
            if not os.path.isdir(model_path_or_name):
                print(f"WARNING: Local model directory not found: {model_path_or_name}. Skipping load.")
                return None, None
        else:
            print(f"Attempting to load model from Hugging Face Hub: {model_path_or_name}")

        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(model_path_or_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_path_or_name)
        model.eval() # Set to evaluation mode

        # --- GPU Check and Placement ---
        if torch.cuda.is_available():
            model.to('cuda')
            print(f"Model '{model_identifier}' moved to GPU.")
        else:
            # --- CORRECTED print statement ---
            print(f"GPU not available, Model '{model_identifier}' using CPU.")
            # ------------------------------
        # --- End GPU Check ---

        print(f"Successfully loaded: '{model_identifier}'")
        return model, tokenizer

    except Exception as e:
        print(f"ERROR: Failed to load model/tokenizer from '{model_identifier}': {e}")
        print(traceback.format_exc()) # Print full traceback for debugging
        return None, None

# --- Function to Load All Defined Models ---
def load_all_models():
    """
    Loads all models defined in MODEL_PATHS into the global LOADED_MODELS dict.
    This should be called once when the application starts (i.e., when this module is imported).
    """
    global LOADED_MODELS # Ensure we are modifying the global dictionary
    print("\n--- Loading all translation models ---")
    if LOADED_MODELS:
        print("Models appear to be already loaded. Skipping.")
        return # Avoid reloading if called multiple times

    available_directions = []
    for direction, path_or_name in MODEL_PATHS.items():
        print(f"\nLoading model for direction: {direction[0]} -> {direction[1]}")
        model, tokenizer = _load_model_and_tokenizer(path_or_name)
        if model and tokenizer:
            LOADED_MODELS[direction] = (model, tokenizer)
            available_directions.append(f"{direction[0]}->{direction[1]}")
        else:
             print(f"--> FAILED to load model for direction {direction[0]} -> {direction[1]}")

    print("\n--------------------------------------")
    if available_directions:
        print(f"Finished loading models. Available translation directions: {', '.join(available_directions)}")
    else:
        print("WARNING: No translation models were successfully loaded.")
    print("--------------------------------------\n")

# --- Main Translation Function ---
def translate(text: str, source_lang: str, target_lang: str) -> str:
    """
    Translates text using the appropriate loaded fine-tuned model
    based on the source and target language codes.

    Args:
        text (str): The text to translate.
        source_lang (str): The source language key (e.g., 'sylheti').
        target_lang (str): The target language key (e.g., 'bengali').

    Returns:
        str: The translated text, or an error message starting with "Error:".
    """
    direction = (source_lang, target_lang)
    print(f"\n--- Attempting translation: {source_lang} -> {target_lang} ---")
    print(f"--- Input text: '{text}'")

    # Check if the required model direction is loaded
    if direction not in LOADED_MODELS:
        error_msg = f"Error: Translation direction ({source_lang} -> {target_lang}) not supported or its model failed to load."
        available = list(LOADED_MODELS.keys())
        if available:
             error_msg += f" Available directions: {available}"
        else:
             error_msg += " No models loaded successfully."
        print(f"--- ERROR: {error_msg} ---")
        return error_msg

    # Retrieve the correct model and tokenizer
    model, tokenizer = LOADED_MODELS[direction]

    # Basic input validation
    if not text or not isinstance(text, str) or not text.strip():
        print("--- Input text is empty or invalid. Returning empty string. ---")
        return ""

    # Perform the translation
    try:
        print(f"--- Using model for {direction}...")
        print(f"--- Preparing input for model...")
        # Ensure tokenizer settings match training (padding, truncation, max_length)
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128) # Use consistent max_length

        # Move input tensors to the same device as the model (CPU or GPU)
        device = model.device # Get the device the model is actually on
        inputs = {k: v.to(device) for k, v in inputs.items()}
        print(f"--- Input tensors moved to device: {device} ---")

        print(f"--- Calling model.generate...")
        with torch.no_grad(): # Disable gradient calculation for inference
            translated_ids = model.generate(
                inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                max_length=128,    # Match training/tokenization setting
                num_beams=4,       # Beam search can improve quality
                early_stopping=True # Stop generation early if EOS token is reached
            )

        print(f"--- Decoding model output...")
        translation = tokenizer.decode(translated_ids[0], skip_special_tokens=True)
        print(f"--- Inference successful for {direction}. Returning: '{translation}'")
        return translation

    except Exception as e:
        print(f"--- ERROR during model inference for {direction} with input '{text}': {e}")
        print(traceback.format_exc()) # Log the full error for debugging
        return f"Error: Translation failed internally for direction {direction}."

# --- Trigger Model Loading on Import ---
# This ensures models are loaded when routes.py imports this module
if __name__ != '__main__': # Only run load_all_models when imported, not if script is run directly
    load_all_models()
else:
    # Optional: Add test code here if you want to run translator.py directly
    print("Running translator.py directly (for testing purposes only).")
    # Make sure models are loaded if run directly too
    if not LOADED_MODELS:
         load_all_models()
    # Example test (requires models to be loaded)
    if ("sylheti", "bengali") in LOADED_MODELS:
         test_text = "মুই বাড়িত যাই"
         print(f"\nTesting Sylheti -> Bengali with: '{test_text}'")
         result = translate(test_text, "sylheti", "bengali")
         print(f"Result: {result}")
    else:
         print("\nSylheti->Bengali model not loaded, skipping direct test.")