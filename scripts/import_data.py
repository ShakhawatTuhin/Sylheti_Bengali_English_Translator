# scripts/import_data.py
import json
import os
import sys

# --- Add project root to sys.path ---
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

from models import Phrase
from config import db, app as flask_app # <-- Use 'app' from config.py, aliased to flask_app

# Adjust JSON file path to be relative to project_root
JSON_DATA_FILE = os.path.join(project_root, 'data', 'sylheti_translation.json')

print(f"Attempting to populate database from: {JSON_DATA_FILE}")
try:
    # Use flask_app (which is the 'app' instance from config.py) for the context
    with flask_app.app_context():
        with open(JSON_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("ERROR: JSON data is not a list of objects as expected.")
        else:
            phrases_added = 0
            phrases_skipped = 0
            for entry in data:
                sylheti_text = entry.get('sylheti')
                bengali_text = entry.get('bengali')
                english_text = entry.get('english')

                if not sylheti_text or not bengali_text:
                    print(f"Skipping entry due to missing Sylheti or Bengali: {entry}")
                    phrases_skipped += 1
                    continue

                # Optional: Check if the phrase already exists to avoid duplicates
                # existing_phrase = Phrase.query.filter_by(SylhetiText=sylheti_text, BengaliText=bengali_text).first()
                # if existing_phrase:
                #     print(f"Skipping duplicate: {sylheti_text[:20]}...")
                #     phrases_skipped +=1
                #     continue

                try:
                    phrase = Phrase(
                        SylhetiText=sylheti_text,
                        BengaliText=bengali_text,
                        EnglishText=english_text
                    )
                    db.session.add(phrase)
                    phrases_added += 1
                except Exception as e_phrase:
                    print(f"Error creating Phrase object for {entry}: {e_phrase}")
                    phrases_skipped += 1
                    db.session.rollback()  # Rollback for this specific item

            db.session.commit()
            print(f"Data import: {phrases_added} phrases added, {phrases_skipped} phrases skipped.")
            print("Data import completed successfully.")

except FileNotFoundError:
    print(f"ERROR: Data file not found at {JSON_DATA_FILE}")
except json.JSONDecodeError:
    print(f"ERROR: Could not decode JSON from {JSON_DATA_FILE}. Check its format.")
except Exception as e:
    print(f"An unexpected error occurred during database population: {e}")
    # It's good practice to rollback if the commit fails or any other major error happens
    # However, db might not be in a state to rollback if connection failed earlier.
    # A more robust setup might initialize db connection within the try block.
    try:
        db.session.rollback()
        print("Rolled back database session due to error.")
    except Exception as rb_error:
        print(f"Error during rollback: {rb_error}")