# scripts/fine_tune_whisper.py
import os
import sys
import torch
from datasets import Dataset, DatasetDict, Audio
from transformers import (
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)
import pandas as pd
import librosa
import evaluate
from transformers.models.whisper.english_normalizer import BasicTextNormalizer
from dataclasses import dataclass
from typing import List, Dict, Union, Any

# Add the parent directory to the sys.path to allow imports from config and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import app, db
from models import AudioFile, Phrase

def fetch_data_from_db():
    """
    Fetches audio file paths and their corresponding transcriptions from the database.
    """
    with app.app_context():
        # Join AudioFile and Phrase tables to get the file path and the Sylheti text
        query = db.session.query(AudioFile.FilePath, Phrase.SylhetiText).join(
            Phrase, AudioFile.PhraseID == Phrase.PhraseID
        )
        data = query.all()
        
        # Create a pandas DataFrame
        df = pd.DataFrame(data, columns=['audio', 'transcription'])
        
        # Ensure the audio paths are absolute
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        df['audio'] = df['audio'].apply(lambda x: os.path.join(project_root, x))
        
        print(f"Fetched {len(df)} records from the database.")
        print(df.head())
        return df

def prepare_dataset(df):
    """
    Converts the DataFrame into a Hugging Face Dataset object, ready for training.
    """
    print("\n--- Preparing Dataset ---")
    # Convert pandas DataFrame to Hugging Face Dataset
    dataset = Dataset.from_pandas(df)
    
    # Resample the audio to 16kHz, which is what Whisper expects
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    
    print("Splitting dataset into training and testing sets (90/10 split).")
    # Split the dataset into 90% for training and 10% for testing/validation
    train_test_split = dataset.train_test_split(test_size=0.1)
    
    datasets = DatasetDict({
        "train": train_test_split["train"],
        "test": train_test_split["test"]
    })

    print("Dataset prepared and split.")
    print(datasets)
    
    # The actual processing (feature extraction and tokenization) will happen
    # inside the Trainer using a data collator.
    return datasets

# We need a Data Collator to perform the feature extraction and tokenization
@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        # split inputs and labels since they have to be of different lengths and need different padding methods
        # first treat the audio inputs by simply returning torch tensors
        input_features = [{"input_features": feature["input_features"]} for feature in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")

        # get the tokenized label sequences
        label_features = [{"input_ids": feature["labels"]} for feature in features]
        # pad the labels to max length
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")

        # replace padding with -100 to ignore loss correctly
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)

        # if bos token is appended in previous tokenization step,
        # cut bos token here as it's append later anyways
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]

        batch["labels"] = labels

        return batch

def main():
    """
    Main function to run the fine-tuning process.
    """
    print("--- Starting Whisper Fine-Tuning Script ---")
    
    # --- Model and Processor Setup ---
    # Use a smaller model to fit into 4GB VRAM
    MODEL_NAME = "openai/whisper-small"
    processor = WhisperProcessor.from_pretrained(MODEL_NAME, language="Bengali", task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME)
    
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []

    # 1. Fetch data from the database
    data_df = fetch_data_from_db()
    if data_df.empty:
        print("No data fetched from database. Exiting.")
        return

    # 2. Prepare the dataset
    sylheti_dataset = prepare_dataset(data_df)
    
    # Pre-process the dataset to prepare it for the model
    def prepare_dataset_for_training(batch):
        audio = batch["audio"]
        batch["input_features"] = processor(audio["array"], sampling_rate=audio["sampling_rate"]).input_features[0]
        batch["labels"] = processor.tokenizer(batch["transcription"]).input_ids
        return batch

    sylheti_dataset = sylheti_dataset.map(prepare_dataset_for_training, remove_columns=sylheti_dataset.column_names["train"], num_proc=1)

    # 3. Define the Data Collator and Trainer
    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)
    
    # Define evaluation metrics
    wer_metric = evaluate.load("wer")

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids

        # replace -100 with the pad_token_id
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id

        # we do not want to group tokens when decoding
        pred_str = processor.batch_decode(pred_ids, skip_special_tokens=True)
        # decode ground truth labels
        label_str = processor.batch_decode(label_ids, skip_special_tokens=True)

        wer = wer_metric.compute(predictions=pred_str, references=label_str)

        return {"wer": wer}

    training_args = Seq2SeqTrainingArguments(
        output_dir="./whisper-sylheti-finetuned",  # change to a repo name of your choice
        per_device_train_batch_size=2, # Reduced for 4GB VRAM
        gradient_accumulation_steps=8,  # Increase accumulation to compensate for small batch size
        learning_rate=1e-5,
        warmup_steps=50,
        max_steps=500, # Set a reasonable number of steps
        gradient_checkpointing=True,
        fp16=True, # Enable mixed-precision training to save memory
        eval_strategy="steps",
        per_device_eval_batch_size=8,
        predict_with_generate=True,
        generation_max_length=225,
        save_steps=100,
        eval_steps=100,
        logging_steps=25,
        report_to=["tensorboard"],
        load_best_model_at_end=True,
        metric_for_best_model="wer",
        greater_is_better=False,
    )

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=sylheti_dataset["train"],
        eval_dataset=sylheti_dataset["test"],
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=processor,
    )

    # 4. Run Fine-Tuning
    print("\n--- Starting Training ---")
    trainer.train()
    print("--- Training Finished ---")

    # 5. Save the fine-tuned model
    print("\n--- Saving Model ---")
    trainer.save_model("models/whisper-medium-sylheti-finetuned")
    processor.save_pretrained("models/whisper-medium-sylheti-finetuned")
    print("--- Model Saved to models/whisper-medium-sylheti-finetuned ---")


if __name__ == "__main__":
    main()