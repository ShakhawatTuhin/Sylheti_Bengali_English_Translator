# sylheti_translator_backend/utils/preprocess.py

from transformers import AutoTokenizer

# --- Constants ---
# Define these here so they can be imported by train.py if needed
# Or define them directly in train.py
MAX_INPUT_LENGTH = 128
MAX_TARGET_LENGTH = 128

# --- Load Tokenizer ---
# Load the tokenizer associated with the *base* model you are fine-tuning from.
# This tokenizer will be saved later *with* the fine-tuned model.

# Use the base model defined in the train script (or load dynamically if needed)
# For simplicity, we assume train.py loads and passes the correct tokenizer instance
# Or, we keep loading the base tokenizer here:
BASE_MODEL_CHECKPOINT = "Helsinki-NLP/opus-mt-bn-en"  # Make sure this is the model you start fine-tuning from in train.py

try:
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_CHECKPOINT)
    print(f"(preprocess.py) Tokenizer loaded for base model: {BASE_MODEL_CHECKPOINT}")
except Exception as e:
    print(f"(preprocess.py) Error loading base tokenizer ({BASE_MODEL_CHECKPOINT}): {e}")
    tokenizer = None
# --- MODIFIED Preprocessing Function ---
# Accepts source and target language keys as arguments
def preprocess_function(examples, src_lang, tgt_lang):
    """
    Tokenizes the source and target text for the seq2seq model.
    Assumes input 'examples' is a dictionary-like object (like a dataset batch).
    Uses the provided src_lang and tgt_lang keys to access the correct text.
    """
    if not tokenizer:
        raise ValueError("Tokenizer is not loaded.")

    # Check if the REQUIRED keys exist in the input data batch using the passed arguments
    if src_lang not in examples:
        # You might see this error if the filtering in train.py failed or keys are wrong
        raise KeyError(f"Source language key '{src_lang}' not found in input examples batch. Available keys: {list(examples.keys())}")
    if tgt_lang not in examples:
         raise KeyError(f"Target language key '{tgt_lang}' not found in input examples batch. Available keys: {list(examples.keys())}")

    # Use the passed arguments to get the correct text columns
    inputs = examples[src_lang]
    targets = examples[tgt_lang]

    # Tokenize inputs
    model_inputs = tokenizer(inputs, max_length=MAX_INPUT_LENGTH, truncation=True)

    # Tokenize targets (labels)
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(targets, max_length=MAX_TARGET_LENGTH, truncation=True)

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs
# --- Data Loading and Mapping ---
# This part is MOVED to train.py. This script only defines the function.
# DO NOT load_dataset or dataset.map here.