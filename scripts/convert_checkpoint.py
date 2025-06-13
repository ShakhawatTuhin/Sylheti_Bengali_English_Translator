# scripts/convert_checkpoint.py
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor
import os

def convert_hf_checkpoint_to_whisper(checkpoint_path, output_path):
    """
    Converts a Hugging Face Whisper checkpoint to a format compatible with
    the original OpenAI whisper library's load_model function.

    Args:
        checkpoint_path (str): Path to the Hugging Face checkpoint directory.
        output_path (str): Path to save the converted .pt model file.
    """
    print(f"--- Starting conversion for checkpoint: {checkpoint_path} ---")

    # 1. Load the fine-tuned model from the Hugging Face checkpoint
    try:
        model = WhisperForConditionalGeneration.from_pretrained(checkpoint_path)
        print("Successfully loaded model from checkpoint.")
    except Exception as e:
        print(f"ERROR: Could not load model from {checkpoint_path}. Make sure the path is correct.")
        print(f"Exception: {e}")
        return

    # 2. Extract the model dimensions and state dictionary
    dims = model.config.to_dict()
    state_dict = model.state_dict()

    # 3. Combine them into the format whisper.load_model expects
    whisper_format_dict = {
        'dims': dims,
        'model_state_dict': state_dict,
    }

    # 4. Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 5. Save the converted model as a .pt file
    try:
        torch.save(whisper_format_dict, output_path)
        print(f"--- Conversion successful! ---")
        print(f"Model saved to: {output_path}")
    except Exception as e:
        print(f"ERROR: Could not save the converted model to {output_path}.")
        print(f"Exception: {e}")

if __name__ == "__main__":
    # The path to your downloaded and unzipped checkpoint folder
    CHECKPOINT_DIR = "./checkpoint-100" 

    # The desired output path for the converted model file.
    # We'll save it in a 'models' directory to keep things organized.
    OUTPUT_FILE = "./models/whisper-medium-sylheti.pt"

    if not os.path.isdir(CHECKPOINT_DIR):
        print(f"ERROR: Checkpoint directory not found at '{CHECKPOINT_DIR}'")
        print("Please make sure you have downloaded, unzipped, and placed the 'checkpoint-100' folder in your project root.")
    else:
        convert_hf_checkpoint_to_whisper(CHECKPOINT_DIR, OUTPUT_FILE) 