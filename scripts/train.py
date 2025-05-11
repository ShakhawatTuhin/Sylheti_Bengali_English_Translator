import os
import numpy as np
import torch
from datasets import load_dataset # Only load_dataset needed from here directly
from transformers import (
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq,
    AutoTokenizer # Use AutoTokenizer here now
)
import argparse # Import argparse for command-line arguments
import evaluate # Use evaluate for metrics
import traceback # For detailed error logging

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="Fine-tune a translation model.")
parser.add_argument("--source_lang", type=str, required=True, help="Source language key in JSON (e.g., 'sylheti', 'bengali', 'english')")
parser.add_argument("--target_lang", type=str, required=True, help="Target language key in JSON (e.g., 'sylheti', 'bengali', 'english')")
parser.add_argument("--data_file", type=str, default="data/sylheti_translation.json", help="Path to the JSON data file.")
parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the fine-tuned model (e.g., models/finetuned_sy_bn).")
parser.add_argument("--base_model", type=str, default="Helsinki-NLP/opus-mt-bn-en", help="Base model checkpoint for fine-tuning.")
parser.add_argument("--num_train_epochs", type=int, default=5, help="Number of training epochs.")
parser.add_argument("--train_batch_size", type=int, default=8, help="Batch size for training.")
parser.add_argument("--eval_batch_size", type=int, default=8, help="Batch size for evaluation.")
parser.add_argument("--learning_rate", type=float, default=2e-5, help="Learning rate.")
parser.add_argument("--weight_decay", type=float, default=0.01, help="Weight decay.")
parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
parser.add_argument("--max_input_length", type=int, default=128, help="Max token length for source.")
parser.add_argument("--max_target_length", type=int, default=128, help="Max token length for target.")
parser.add_argument("--test_split_size", type=float, default=0.1, help="Fraction of data for validation set (0.0 to 1.0).")

args = parser.parse_args()

# --- Use Parsed Arguments ---
SRC_LANG = args.source_lang
TGT_LANG = args.target_lang
TRAIN_DATA_PATH = args.data_file
OUTPUT_DIR = args.output_dir
BASE_MODEL_CHECKPOINT = args.base_model
NUM_TRAIN_EPOCHS = args.num_train_epochs
TRAIN_BATCH_SIZE = args.train_batch_size
EVAL_BATCH_SIZE = args.eval_batch_size
LEARNING_RATE = args.learning_rate
WEIGHT_DECAY = args.weight_decay
RANDOM_SEED = args.seed
MAX_INPUT_LENGTH = args.max_input_length
MAX_TARGET_LENGTH = args.max_target_length
TEST_SPLIT_SIZE = args.test_split_size

LOGGING_DIR = os.path.join(OUTPUT_DIR, "logs") # Log within output dir

print(f"\n--- Training Configuration ---")
print(f"Source Language: {SRC_LANG}")
print(f"Target Language: {TGT_LANG}")
print(f"Data File: {TRAIN_DATA_PATH}")
print(f"Base Model: {BASE_MODEL_CHECKPOINT}")
print(f"Output Directory: {OUTPUT_DIR}")
print(f"Epochs: {NUM_TRAIN_EPOCHS}, Train Batch: {TRAIN_BATCH_SIZE}, Eval Batch: {EVAL_BATCH_SIZE}, LR: {LEARNING_RATE}")
print(f"Seed: {RANDOM_SEED}")
print(f"-----------------------------\n")


# --- Import the MODIFIED preprocess_function (ensure it accepts src/tgt args) ---
try:
    # The preprocess_function itself is needed, tokenizer loaded below
    from utils.preprocess import preprocess_function
except ImportError:
    print("ERROR: Could not import 'preprocess_function' from utils.preprocess.")
    print("Ensure utils/preprocess.py exists and preprocess_function accepts 'examples, src_lang, tgt_lang'.")
    exit()
except Exception as e:
    print(f"Error during import from utils.preprocess: {e}")
    exit()


# --- Create Directories ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOGGING_DIR, exist_ok=True)


# --- Load Tokenizer (Load here based on base model argument) ---
print(f"Loading Tokenizer for base model: {BASE_MODEL_CHECKPOINT}")
try:
    # Load the specific tokenizer for the base model being used
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_CHECKPOINT)
except Exception as e:
    print(f"Error loading base tokenizer ({BASE_MODEL_CHECKPOINT}): {e}")
    exit()


# --- 1. Load and Filter Data ---
print(f"Loading dataset from: {TRAIN_DATA_PATH}")
try:
    # Load the full dataset
    dataset = load_dataset("json", data_files=TRAIN_DATA_PATH, split="train")
    print(f"Initial dataset loaded with {len(dataset)} examples.")

    # Filter out rows where the specific source or target language for THIS run is missing/null/empty
    print(f"Filtering dataset for non-empty '{SRC_LANG}' and '{TGT_LANG}' columns...")
    original_count = len(dataset)

    def filter_row(example):
        src_ok = example.get(SRC_LANG) is not None and example[SRC_LANG] != ""
        tgt_ok = example.get(TGT_LANG) is not None and example[TGT_LANG] != ""
        return src_ok and tgt_ok

    dataset = dataset.filter(filter_row)
    filtered_count = len(dataset)
    print(f"Filtered dataset size: {filtered_count} (Removed {original_count - filtered_count} rows with missing data for this pair)")

    if filtered_count == 0:
        print(f"CRITICAL ERROR: No valid data found for the pair {SRC_LANG} -> {TGT_LANG} after filtering.")
        print(f"Check your data file ('{TRAIN_DATA_PATH}') and ensure columns '{SRC_LANG}' and '{TGT_LANG}' exist and have non-empty values.")
        exit()

except Exception as e:
    print(f"Error loading or filtering dataset: {e}")
    print(traceback.format_exc())
    exit()

# Split dataset
print(f"Splitting dataset ({1-TEST_SPLIT_SIZE:.0%} train / {TEST_SPLIT_SIZE:.0%} validation)...")
if filtered_count < 2 : # Need at least 2 samples to split
     print("Warning: Dataset too small to split. Using all data for training and evaluation (not recommended).")
     train_dataset_raw = dataset
     eval_dataset_raw = dataset
else:
    split_dataset = dataset.train_test_split(test_size=TEST_SPLIT_SIZE, seed=RANDOM_SEED)
    train_dataset_raw = split_dataset["train"]
    eval_dataset_raw = split_dataset["test"]

print(f"Train samples: {len(train_dataset_raw)}, Validation samples: {len(eval_dataset_raw)}")


# --- 2. Apply Preprocessing ---
# Uses preprocess_function imported from utils.preprocess
# Pass SRC_LANG and TGT_LANG from args to the function via fn_kwargs
print("Applying preprocessing function to datasets...")
fn_kwargs = {'src_lang': SRC_LANG, 'tgt_lang': TGT_LANG}
try:
    tokenized_train_dataset = train_dataset_raw.map(
        preprocess_function,
        batched=True,
        remove_columns=train_dataset_raw.column_names, # Keep only model inputs
        fn_kwargs=fn_kwargs # Pass the arguments here
    )
    tokenized_eval_dataset = eval_dataset_raw.map(
        preprocess_function,
        batched=True,
        remove_columns=eval_dataset_raw.column_names, # Keep only model inputs
        fn_kwargs=fn_kwargs # Pass the arguments here
    )
    print("Preprocessing complete.")
except KeyError as e:
    print(f"\nPREPROCESSING ERROR: Missing key during tokenization: {e}")
    print("This likely means 'preprocess_function' in utils/preprocess.py is not using the passed src/tgt languages correctly.")
    print(f"Check that it uses the passed '{SRC_LANG}' and '{TGT_LANG}' keys.")
    exit()
except Exception as e:
    print(f"\nError during preprocessing: {e}")
    print(traceback.format_exc())
    exit()


# --- 3. Load Base Model ---
print(f"Loading base model for fine-tuning: {BASE_MODEL_CHECKPOINT}")
try:
    model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL_CHECKPOINT)
except Exception as e:
    print(f"Error loading base model: {e}")
    print(traceback.format_exc())
    exit()

# --- 4. Data Collator ---
# Handles dynamic padding of batches
data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)
print("Data collator initialized.")

# --- 5. Evaluation Metric (BLEU/SacreBLEU) ---
print("Loading SacreBLEU metric...")
metric = None # Initialize metric to None
try:
    metric = evaluate.load("sacrebleu")
    print("Using 'evaluate' library for SacreBLEU.")
except Exception as e:
    print(f"Could not load SacreBLEU metric using 'evaluate': {e}")
    print("Evaluation during training might not report BLEU scores.")
    print("Attempting fallback using 'datasets.load_metric' (deprecated)...")
    try:
        from datasets import load_metric
        metric = load_metric("sacrebleu")
        print("Using 'datasets.load_metric' for SacreBLEU (fallback).")
    except Exception as e2:
         print(f"Could not load SacreBLEU metric using datasets.load_metric either: {e2}")


def postprocess_text(preds, labels):
    preds = [pred.strip() for pred in preds]
    labels = [[label.strip()] for label in labels] # sacrebleu expects list of references
    return preds, labels

def compute_metrics(eval_preds):
    # print("\n--- compute_metrics called ---") # Optional: uncomment for verbose debugging
    if metric is None:
         # print("--- compute_metrics: Metric object is None, returning {} ---")
         return {}

    preds, labels = eval_preds
    if isinstance(preds, tuple):
        preds = preds[0]

    # Replace -100 (ignore index) with pad_token_id for decoding
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)

    try:
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    except Exception as e:
        print(f"\nERROR during decoding in compute_metrics: {e}")
        return {} # Return empty dict if decoding fails

    try:
        # Simple post-processing
        processed_preds, processed_labels = postprocess_text(decoded_preds, decoded_labels)

        # Compute BLEU score
        result = metric.compute(predictions=processed_preds, references=processed_labels)

        # Extract main score
        if result and "score" in result:
            bleu_score = result["score"]
            result_dict = {"bleu": bleu_score}
        else:
            print(f"WARNING: 'score' key not found in SacreBLEU result: {result}")
            result_dict = {}

        # Add generation length metric
        try:
            prediction_lens = [np.count_nonzero(pred != tokenizer.pad_token_id) for pred in preds]
            result_dict["gen_len"] = np.mean(prediction_lens)
        except Exception as e_len:
             print(f"Warning: Could not compute gen_len: {e_len}")


        result_dict = {k: round(v, 4) for k, v in result_dict.items()}
        # print(f"--- compute_metrics returning: {result_dict} ---") # Optional: uncomment for verbose debugging
        return result_dict

    except Exception as e:
        print(f"\nERROR during metric computation or processing: {e}")
        print(f"Failed on Preds (first 3): {decoded_preds[:3]}")
        print(f"Failed on Labels (first 3): {decoded_labels[:3]}")
        return {}


# --- 6. Training Arguments ---
print("Defining training arguments...")
training_args = Seq2SeqTrainingArguments(
    output_dir=OUTPUT_DIR,
    evaluation_strategy="epoch",
    learning_rate=LEARNING_RATE,
    per_device_train_batch_size=TRAIN_BATCH_SIZE,
    per_device_eval_batch_size=EVAL_BATCH_SIZE,
    weight_decay=WEIGHT_DECAY,
    save_strategy="epoch",
    save_total_limit=2, # Saves last 2 checkpoints + best model if load_best_model_at_end=True
    num_train_epochs=NUM_TRAIN_EPOCHS,
    predict_with_generate=True,
    logging_dir=LOGGING_DIR,
    logging_strategy="steps",
    logging_steps=100, # Log training loss every 100 steps
    load_best_model_at_end=True,
    metric_for_best_model="bleu" if metric is not None else "loss", # Use bleu if metric loaded, else loss
    greater_is_better=True if metric is not None else False,      # Higher BLEU is better, lower loss is better
    fp16=torch.cuda.is_available(), # Use mixed precision if GPU available
    report_to="tensorboard", # Or "none" or "wandb"
    seed=RANDOM_SEED,
)

# --- 7. Trainer ---
print("Initializing Trainer...")
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train_dataset,
    eval_dataset=tokenized_eval_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics if metric is not None else None # Only pass if metric loaded
)

# --- 8. Train ---
print("\n" + "*"*30)
print(f"Starting Training for {SRC_LANG} -> {TGT_LANG}")
print("*"*30 + "\n")
train_result = None # Initialize to handle potential errors
try:
    train_result = trainer.train()
    print("Training finished successfully.")

except Exception as e:
    print(f"\nCRITICAL ERROR during training: {e}")
    print(traceback.format_exc())
    print("\nTraining stopped prematurely due to error.")


# --- 9. Save Final Model & Metrics (Only if training started) ---
if train_result is not None:
    print("Saving the best model found during training...")
    try:
        # If load_best_model_at_end=True, the best model is already loaded.
        # trainer.save_model() will save the currently loaded model (which should be the best one)
        trainer.save_model(OUTPUT_DIR) # Saves model, tokenizer, config etc. to the specified output_dir
        print(f"Best model saved to: {OUTPUT_DIR}")

        # Save training metrics
        metrics = train_result.metrics
        trainer.log_metrics("train", metrics)
        trainer.save_metrics("train", metrics)

    except Exception as e:
        print(f"\nError during final model saving: {e}")
        print(traceback.format_exc())

    # --- 10. Evaluate Final Model (Optional but recommended) ---
    print("\nEvaluating the final model on the validation set...")
    try:
        eval_metrics = trainer.evaluate(eval_dataset=tokenized_eval_dataset, metric_key_prefix="final_eval")
        trainer.log_metrics("final_eval", eval_metrics)
        trainer.save_metrics("final_eval", eval_metrics)
        print("Final evaluation complete.")
    except Exception as e:
         print(f"\nError during final evaluation: {e}")
         print(traceback.format_exc())

else:
     print("\nSkipping final save/evaluation because training did not complete successfully.")


print(f"\nTraining script finished for {SRC_LANG} -> {TGT_LANG}.")