import os # Import the 'os' module to access environment variables
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv # Import load_dotenv

print("--- config.py: STARTING TO LOAD ---")

# --- Load environment variables from .env file (for local development) ---
# This should be one of the first things you do
load_dotenv()
print("--- config.py: .env file loaded (if present) ---")

app = Flask(__name__)

# --- Database Configuration using Environment Variable ---
# Get the DATABASE_URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("--- config.py: WARNING: DATABASE_URL environment variable not set. ---")
    # You can choose to:
    # 1. Raise an error if it's absolutely required for production
    #    raise ValueError("CRITICAL: DATABASE_URL environment variable is not set!")
    # 2. Use a default local development URI (less secure if accidentally used in prod)
    print("--- config.py: Using default local development PostgreSQL URI. ---")
    DATABASE_URL = 'postgresql://postgres:tuhinpostgre@localhost/sylhetitranslationdb' # FOR LOCAL DEV ONLY
else:
    print(f"--- config.py: DATABASE_URL found in environment: {DATABASE_URL[:30]}... (partially shown for security)")


app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

print(f"--- config.py: 'db' object created. ID: {id(db)} ---")
print("--- config.py: app and db INITIALIZED ---")

# Define init_db function
def init_db():
    print("--- config.py: init_db() CALLED ---") # Removed (SIMPLIFIED MODELS) for clarity
    try:
        print("--- config.py: init_db(): ATTEMPTING TO IMPORT MODELS ---")
        # Import all your models that need tables created
        from models import Phrase, Speaker, AudioFile
        print("--- config.py: init_db(): Models (Phrase, Speaker, AudioFile) IMPORTED SUCCESSFULLY ---")
        print(f"--- config.py: init_db(): Tables known to SQLAlchemy metadata BEFORE create_all: {list(db.metadata.tables.keys())} ---")

    except ImportError as e:
        print(f"--- config.py: init_db(): FAILED TO IMPORT MODELS. Error: {e} ---")
        raise

    print("--- config.py: init_db(): Calling db.create_all() ---")
    db.create_all()
    print(f"--- config.py: init_db(): Tables known to SQLAlchemy metadata AFTER create_all: {list(db.metadata.tables.keys())} ---")
    print("--- config.py: init_db(): db.create_all() EXECUTED (check SQL logs) ---")

# Script Execution Block
if __name__ == '__main__':
    print("--- config.py: __main__ BLOCK ENTERED ---")
    with app.app_context():
        print("--- config.py: __main__: App context entered, calling init_db() ---")
        init_db()
    print("--- config.py: __main__ BLOCK FINISHED ---")

print("--- config.py: FINISHED LOADING (if imported) or FINISHED EXECUTION (if run directly) ---")