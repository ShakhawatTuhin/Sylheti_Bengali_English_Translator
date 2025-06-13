# scripts/add_audio_data.py

import os
import sys

# Add the parent directory to the sys.path to allow imports from config and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import db, app
from models import Phrase, Speaker, AudioFile

def add_audio_entry(phrase_id: int, speaker_id: int, file_path: str):
    """
    Adds an audio file reference to the database.
    """
    # Basic validation (can be expanded)
    if not os.path.exists(file_path):
        print(f"Error: Audio file does not exist at '{file_path}'. Skipping.")
        return

    # Check if Phrase and Speaker exist (optional but recommended)
    phrase = Phrase.query.get(phrase_id)
    if not phrase:
        print(f"Error: Phrase with ID {phrase_id} not found. Skipping audio entry for '{file_path}'.")
        return

    speaker = Speaker.query.get(speaker_id)
    if not speaker:
        print(f"Error: Speaker with ID {speaker_id} not found. Skipping audio entry for '{file_path}'.")
        return

    # Check if this specific audio entry already exists to prevent duplicates
    existing_entry = AudioFile.query.filter_by(PhraseID=phrase_id, SpeakerID=speaker_id, FilePath=file_path).first()
    if existing_entry:
        print(f"Info: Audio entry for PhraseID {phrase_id}, SpeakerID {speaker_id}, FilePath '{file_path}' already exists. Skipping.")
        return

    try:
        new_audio = AudioFile(PhraseID=phrase_id, SpeakerID=speaker_id, FilePath=file_path)
        db.session.add(new_audio)
        db.session.commit()
        print(f"Successfully added audio entry: PhraseID={phrase_id}, SpeakerID={speaker_id}, FilePath='{file_path}'")
    except Exception as e:
        db.session.rollback()
        print(f"Failed to add audio entry for {file_path}: {e}")


if __name__ == "__main__":
    with app.app_context():
    print("--- Running add_audio_data.py ---")
    print("This script helps populate the AudioFiles table.")
    print("Ensure your audio files are in a structured directory (e.g., data/audio/sylheti/).")
    print("Ensure Phrases and Speakers are already in your database.")

    # --- IMPORTANT: Configure your audio data here ---
    # This is a list of tuples: (phrase_id, speaker_id, relative_path_to_audio_file)
    # Replace these with your actual data!

    # Example: First, add some dummy phrases and speakers if you haven't already done it via API/init_db.py
    # This part is just for demonstration if your DB is empty. Remove in production use.
        try:
            # Add dummy phrase
            if not Phrase.query.filter_by(SylhetiText="মুই ভাত খাই").first():
                db.session.add(Phrase(SylhetiText="মুই ভাত খাই", BengaliText="আমি ভাত খাই", EnglishText="I eat rice"))
                db.session.commit()
                print("Added dummy phrase.")
            dummy_phrase_id = Phrase.query.filter_by(SylhetiText="মুই ভাত খাই").first().PhraseID

            # Add dummy speaker
            if not Speaker.query.filter_by(Name="Test Speaker A").first():
                db.session.add(Speaker(Name="Test Speaker A", Gender="Male"))
                db.session.commit()
                print("Added dummy speaker.")
            dummy_speaker_id_a = Speaker.query.filter_by(Name="Test Speaker A").first().SpeakerID

            if not Speaker.query.filter_by(Name="Test Speaker B").first():
                db.session.add(Speaker(Name="Test Speaker B", Gender="Female"))
                db.session.commit()
                print("Added dummy speaker B.")
            dummy_speaker_id_b = Speaker.query.filter_by(Name="Test Speaker B").first().SpeakerID

        except Exception as e:
            db.session.rollback()
            print(f"Error setting up dummy data: {e}")
            #sys.exit(1) # Exit if essential dummy data setup fails
    # --------------------------------------------------------------------------

    # Define your actual audio data entries here
    # Make sure the `file_path` is relative to your project root or an absolute path.
    # Example: If your audio is in sylheti_translator_backend/data/audio/sylheti/
    # and the file is phrase1_speaker1.wav, the path would be "data/audio/sylheti/phrase1_speaker1.wav"
    audio_entries_to_add = [
            (i, 1, f"data/audio/speaker_muniat/{i}.mp3") for i in range(1, 32)
        ] + [
            (i, 2, f"data/audio/speaker_tuhin/{i}.mp3") for i in range(1, 40)
    ]

    # --- Run the additions ---
    if not audio_entries_to_add:
        print("No audio entries defined in the script. Please update 'audio_entries_to_add'.")
    else:
        for phrase_id, speaker_id, file_path in audio_entries_to_add:
            add_audio_entry(phrase_id, speaker_id, file_path)

    print("--- Finished add_audio_data.py ---") 