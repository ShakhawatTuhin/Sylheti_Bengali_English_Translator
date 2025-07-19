# scripts/translator.py

import os
import traceback
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

LOADED_MODELS = {}

HF_USERNAME = "ShakhawatTuhin" # Your HF username

# Define MODEL_PATHS. For each entry, the value is the model identifier.
# If it's a Hugging Face Hub ID, use "username/repo_name".
# If it's a local path, use a relative path like "../models/your_model_dir".
MODEL_PATHS = {
    # --- SYLHETI AS SOURCE ---
    ("sylheti", "bengali"): "../models/sy_bn_1396",  # Using local path that matches directory structure

    ("sylheti", "english"): "../models/sy_en_1396",  # Using local path that matches directory structure

    # --- SYLHETI AS TARGET ---
    ("bengali", "sylheti"): "../models/bn_sy_1396",  # Using local path that matches directory structure

    # Use local path for English to Sylheti
    ("english", "sylheti"): "../models/en_sy_1396",  # Using local path that matches directory structure
    
    # English to Bengali and Bengali to English will fall back to Hugging Face if we can't find them locally
    ("english", "bengali"): f"{HF_USERNAME}/sylheti_translator_en_bn_1396",
    ("bengali", "english"): f"{HF_USERNAME}/sylheti_translator_bn_en_1396",
}

# --- Helper Function to Load a Single Model ---
def _load_model_and_tokenizer(model_path_or_hub_id, direction_key_for_logging="N/A"):
    """
    Loads a single model and tokenizer.
    It intelligently tries to load as a local path first if it looks like one,
    otherwise assumes it's a Hugging Face Hub identifier.
    """
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    model_to_load = model_path_or_hub_id
    attempt_type = "Hugging Face Hub" # Default assumption

    # Heuristic: If it starts with '../' or './' or contains os path separators,
    # treat it as a potential local path first.
    if model_path_or_hub_id.startswith(("../", "./")) or \
       os.path.sep in model_path_or_hub_id or \
       (os.altsep and os.altsep in model_path_or_hub_id):

        potential_local_path = os.path.abspath(os.path.join(current_script_dir, model_path_or_hub_id))
        print(f"({direction_key_for_logging}) Path '{model_path_or_hub_id}' looks like a local path. Resolved to: {potential_local_path}")
        if os.path.isdir(potential_local_path):
            model_to_load = potential_local_path
            attempt_type = "LOCAL"
            print(f"({direction_key_for_logging}) Found local directory. Attempting to load from: {model_to_load}")
        else:
            print(f"({direction_key_for_logging}) WARNING: Local path '{potential_local_path}' not found as a directory. Will attempt '{model_path_or_hub_id}' as a Hub ID.")
            # model_to_load remains model_path_or_hub_id, attempt_type remains Hub
    else:
        print(f"({direction_key_for_logging}) Assuming '{model_path_or_hub_id}' is a Hugging Face Hub identifier.")

    try:
        print(f"({direction_key_for_logging}) Attempting to load via transformers from: '{model_to_load}' (as {attempt_type})")
        tokenizer = AutoTokenizer.from_pretrained(model_to_load)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_to_load)
        model.eval()

        if torch.cuda.is_available():
            model.to('cuda')
            print(f"({direction_key_for_logging}) Model '{model_path_or_hub_id}' moved to GPU.")
        else:
            print(f"({direction_key_for_logging}) GPU not available, Model '{model_path_or_hub_id}' using CPU.")

        print(f"({direction_key_for_logging}) Successfully loaded '{model_path_or_hub_id}' (from source: {model_to_load} as {attempt_type}).")
        return model, tokenizer

    except Exception as e:
        print(f"ERROR ({direction_key_for_logging}): Failed to load model/tokenizer from '{model_to_load}' (intended as {attempt_type}). Error: {e}")
        # If the determined attempt (e.g. local) failed, and model_to_load is different from model_path_or_hub_id,
        # it means our local path resolution failed. We could try the original as a Hub ID if it's not what we just tried.
        # This can get complex, for now, the primary attempt based on heuristic is logged.
        # If attempt_type was "LOCAL" and it failed, and model_path_or_hub_id doesn't look like a path,
        # one could add a secondary attempt here to load model_path_or_hub_id from Hub.
        # For simplicity now, if the primary determined path fails, it fails for this function call.
        print(traceback.format_exc())
        return None, None


# --- Function to Load All Defined Models ---
def load_all_models():
    global LOADED_MODELS
    print("\n--- Loading all translation models ---")
    if LOADED_MODELS:
        print("Models appear to be already loaded or an attempt was made. Skipping reload. Restart app to force reload.")
        return

    available_directions = []
    for direction_key, path_or_hub_id_from_config in MODEL_PATHS.items():
        # Ensure direction_key is a tuple of two strings for logging
        if isinstance(direction_key, tuple) and len(direction_key) == 2:
            direction_str = f"{direction_key[0]} -> {direction_key[1]}"
        else:
            direction_str = str(direction_key) # Fallback if key is not as expected

        print(f"\nLoading model for direction: {direction_str} (Configured as: '{path_or_hub_id_from_config}')")
        model, tokenizer = _load_model_and_tokenizer(path_or_hub_id_from_config, direction_key_for_logging=direction_str)

        if model and tokenizer:
            LOADED_MODELS[direction_key] = (model, tokenizer)
            available_directions.append(direction_str)
        else:
            print(f"--> FAILED to load model for direction {direction_str}")

    print("\n--------------------------------------")
    if available_directions:
        print(f"Finished loading models. Available translation directions: {', '.join(available_directions)}")
    else:
        print("CRITICAL WARNING: No translation models were successfully loaded.")
    print("--------------------------------------\n")


# --- Main Translation Function --- (This should remain largely unchanged from your working version)
def translate(text: str, source_lang: str, target_lang: str) -> str:
    direction = (source_lang, target_lang)
    print(f"\n--- Attempting translation: {source_lang} -> {target_lang} ---")

    # Clean the input text first
    cleaned_text = text.strip() if isinstance(text, str) else ""

    print(f"--- Input text: '{cleaned_text}' (Original: '{text}')")

    if direction not in LOADED_MODELS:
        error_msg = f"Error: Translation direction ({source_lang} -> {target_lang}) not supported or its model failed to load."
        available = [f"{k[0]}->{k[1]}" for k in LOADED_MODELS.keys() if isinstance(k, tuple) and len(k) == 2]
        if available:
             error_msg += f" Available directions: {', '.join(available)}"
        else:
             error_msg += " No models loaded successfully."
        print(f"--- ERROR: {error_msg} ---")
        return error_msg

    model, tokenizer = LOADED_MODELS[direction]

    if not cleaned_text:
        print("--- Input text is empty or invalid. Returning empty string. ---")
        return ""
    try:
        print(f"--- Using model for {direction}...")
        
        # Debug tokenization
        print(f"--- Tokenizing: '{cleaned_text}'")
        tokens = tokenizer.tokenize(cleaned_text)
        print(f"--- Tokens: {tokens}")
        
        inputs = tokenizer(cleaned_text, return_tensors="pt", padding=True, truncation=True, max_length=128)
        device = model.device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        print(f"--- Input tensors moved to device: {device} ---")
        print(f"--- Calling model.generate...")
        
        with torch.no_grad():
            translated_ids = model.generate(
                inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                max_length=128,
                num_beams=4,
                early_stopping=True
            )
        print(f"--- Decoding model output...")
        translation = tokenizer.decode(translated_ids[0], skip_special_tokens=True)
        
        # Additional debugging
        if not translation or translation == "?" or translation.strip() == "":
            print(f"--- WARNING: Empty or question mark translation produced. Raw output tensor: {translated_ids[0]} ---")
            # Try alternative decoding approach
            print(f"--- Attempting alternative decoding approach...")
            translation_alt = tokenizer.convert_ids_to_tokens(translated_ids[0])
            print(f"--- Alternative decoding tokens: {translation_alt}")
            
            # Check if we have only a few tokens that might be special tokens
            if len(translated_ids[0]) < 5:
                print(f"--- Very short translation output. This may indicate a model issue or unexpected input format ---")
        
        print(f"--- Inference successful for {direction}. Returning: '{translation}'")
        return translation
    except Exception as e:
        print(f"--- ERROR during model inference for {direction} with input '{text}': {e}")
        print(traceback.format_exc())
        return f"Error: Translation failed internally for direction {direction}."


# --- Trigger Model Loading on Import ---
if __name__ != '__main__':
    load_all_models()
else:
    print("Running translator.py directly (for testing purposes only).")
    if not LOADED_MODELS:
         load_all_models()
    # Example test
    if ("bengali", "sylheti") in LOADED_MODELS: # Test a direction you expect to work
         test_text = "আমি ভাত খাই" # Example Bengali
         print(f"\nTesting Bengali -> Sylheti with: '{test_text}'")
         result = translate(test_text, "bengali", "sylheti")
         print(f"Result: {result}")
    else:
         print("\nBengali->Sylheti model not loaded, skipping direct test.")