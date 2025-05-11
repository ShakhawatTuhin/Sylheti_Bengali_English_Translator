# config.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

print("--- config.py: STARTING TO LOAD ---")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:tuhinpostgre@localhost/sylhetitranslationdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

print(f"--- config.py: 'db' object created. ID: {id(db)} ---")
print("--- config.py: app and db INITIALIZED ---")

# 4. Define init_db function
def init_db():
    print("--- config.py: init_db() CALLED (SIMPLIFIED MODELS) ---")
    try:
        print("--- config.py: init_db(): ATTEMPTING TO IMPORT SIMPLIFIED MODELS ---")
        from models import Phrase # << ONLY IMPORT PHRASE FOR NOW
        print("--- config.py: init_db(): SIMPLIFIED Phrase MODEL IMPORTED SUCCESSFULLY ---")
        print(f"--- config.py: init_db(): Type of Phrase model: {type(Phrase)} ---") # New print
        print(f"--- config.py: init_db(): Is Phrase a subclass of db.Model? {issubclass(Phrase, db.Model)} ---") # New print
        print(f"--- config.py: init_db(): Tables known to SQLAlchemy metadata BEFORE create_all: {db.metadata.tables.keys()} ---") # New print

    except ImportError as e:
        print(f"--- config.py: init_db(): FAILED TO IMPORT MODELS. Error: {e} ---")
        raise

    print("--- config.py: init_db(): Calling db.create_all() (SIMPLIFIED MODELS) ---")
    db.create_all()
    print(f"--- config.py: init_db(): Tables known to SQLAlchemy metadata AFTER create_all: {db.metadata.tables.keys()} ---") # New print
    print("--- config.py: init_db(): db.create_all() EXECUTED (SIMPLIFIED MODELS - check SQL logs) ---")

# ... (rest of config.py, including the __main__ block) ...
# 6. Script Execution Block
if __name__ == '__main__':
    print("--- config.py: __main__ BLOCK ENTERED ---")
    # It's crucial that db.create_all() (called by init_db)
    # runs within an app context.
    with app.app_context():
        print("--- config.py: __main__: App context entered, calling init_db() ---")
        init_db()
    print("--- config.py: __main__ BLOCK FINISHED ---")

print("--- config.py: FINISHED LOADING (if imported) or FINISHED EXECUTION (if run directly) ---")