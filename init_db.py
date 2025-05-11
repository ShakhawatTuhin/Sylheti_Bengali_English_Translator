# init_db.py
from config import app, db
from models import Phrase, Speaker, AudioFile

print("--- init_db.py: Starting DB Initialization ---")

with app.app_context():
    print(f"--- init_db.py: Inside app context ---")
    print(f"--- Phrase is subclass of db.Model? {issubclass(Phrase, db.Model)} ---")
    print(f"--- Tables BEFORE: {db.metadata.tables.keys()} ---")
    db.create_all()
    print(f"--- Tables AFTER: {db.metadata.tables.keys()} ---")

print("--- init_db.py: Done ---")
