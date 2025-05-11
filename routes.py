# sylheti_translator_backend/routes.py

from flask import Blueprint, request, jsonify, render_template
from config import db # Database interaction needed for other routes
from models import Phrase, Speaker, AudioFile # Models needed for other routes
import traceback # For logging detailed errors if needed

# --- Import the unified translation function ---
# Assumes your inference script is now named 'translator.py'
# And it contains the function 'translate(text, source_lang, target_lang)'
# And it loads all necessary models when imported.
try:
    from scripts.translator import translate
    print("Successfully imported 'translate' from scripts.translator")
except ImportError:
    print("--------------------------------------------------------------------")
    print("WARNING: Could not import 'translate' from scripts.translator.")
    print("Ensure translator.py exists, has the translate function, and loads models.")
    print("Translation API endpoint (/translate) will return an error.")
    print("--------------------------------------------------------------------")
    # Define a dummy function so the app doesn't crash on startup
    def translate(text, source_lang, target_lang):
        # In a real scenario, you might want the app to fail loudly here
        # depending on how critical translation is at startup.
        print(f"ERROR: Attempted to call dummy translate function for {source_lang}->{target_lang}")
        return "Error: Translation module failed to load on server startup."
except Exception as e:
     print(f"An unexpected error occurred during import from scripts.translator: {e}")
     print(traceback.format_exc())
     def translate(text, source_lang, target_lang):
         return f"Error: Unexpected error loading translation module ({type(e).__name__})."


# --- Create the Blueprint (Define only ONCE) ---
routes_bp = Blueprint("routes", __name__)

# --- Frontend Route ---
@routes_bp.route("/")
def index():
    """Serves the main HTML page."""
    return render_template("index.html")


# --- UPDATED Multi-Directional Translation API Endpoint ---
@routes_bp.route("/translate", methods=["POST"])
def translate_text_api():
    """
    Receives text, source language, and target language,
    and returns translation using the appropriate fine-tuned model.
    Expects JSON: {"text": "...", "source_lang": "...", "target_lang": "..."}
    """
    # Add print statements for debugging API calls
    print(f"\n--- ENTERING /translate route ---")
    endpoint_error_prefix = "API Error:" # Consistent prefix for user-facing errors from this endpoint

    if not request.is_json:
         print(f"--- Route Error: Request not JSON ---")
         return jsonify({"error": f"{endpoint_error_prefix} Request must be JSON"}), 415

    data = request.get_json()
    text_to_translate = data.get("text")
    source_language = data.get("source_lang") # Expecting 'sylheti', 'bengali', 'english'
    target_language = data.get("target_lang") # Expecting 'sylheti', 'bengali', 'english'

    print(f"--- Route received: text='{text_to_translate}', source='{source_language}', target='{target_language}' ---")

    # --- Input Validation ---
    if not text_to_translate: # Check if text exists and is not just whitespace
         print(f"--- Route Error: 'text' field missing or empty ---")
         return jsonify({"error": f"{endpoint_error_prefix} Required field 'text' is missing or empty"}), 400
    if not source_language:
        print(f"--- Route Error: 'source_lang' field missing ---")
        return jsonify({"error": f"{endpoint_error_prefix} Required field 'source_lang' is missing"}), 400
    if not target_language:
        print(f"--- Route Error: 'target_lang' field missing ---")
        return jsonify({"error": f"{endpoint_error_prefix} Required field 'target_lang' is missing"}), 400
    # Optional: Validate language codes if needed
    # valid_langs = ['sylheti', 'bengali', 'english']
    # if source_language not in valid_langs or target_language not in valid_langs:
    #     return jsonify({"error": f"{endpoint_error_prefix} Invalid source or target language specified"}), 400
    if source_language == target_language:
         return jsonify({"error": f"{endpoint_error_prefix} Source and target languages cannot be the same"}), 400
    # --- End Input Validation ---


    # --- Call the unified translation function ---
    try:
        print(f"--- Route calling translator.translate function... ---")
        translation_result = translate(
            text=text_to_translate,
            source_lang=source_language,
            target_lang=target_language
        )
        print(f"--- Route received result from translator: '{translation_result}' ---")

        # Check if the translator function itself returned an error string
        # (e.g., model not loaded, direction not supported, inference failed)
        if isinstance(translation_result, str) and translation_result.startswith("Error:"):
             print(f"--- Route reporting error from translator module ---")
             # Pass the specific error from the translator module back to the client
             # Decide on appropriate status code based on error type
             status_code = 400 if "not supported" in translation_result else 500
             return jsonify({"error": translation_result}), status_code

        # --- Success Case ---
        print(f"--- Route returning successful translation ---")
        return jsonify({"translation": translation_result})

    except Exception as e:
        # Catch any unexpected errors during the call to translate()
        print(f"--- UNEXPECTED ERROR in /translate route while calling translator: {e} ---")
        print(traceback.format_exc())
        return jsonify({"error": f"{endpoint_error_prefix} An internal server error occurred during translation."}), 500
    # --- End Call to translation function ---


# === Database Management Routes (Keep these as they are) ===

# Get all Phrases
@routes_bp.route("/phrases", methods=["GET"])
def get_phrases():
    """Returns all phrases currently in the database."""
    try:
        phrases = Phrase.query.all()
        return jsonify([
            {"PhraseID": p.PhraseID, "SylhetiText": p.SylhetiText, "BengaliText": p.BengaliText, "EnglishText": p.EnglishText}
            for p in phrases
        ])
    except Exception as e:
        print(f"Error fetching phrases: {e}")
        return jsonify({"error": "Could not retrieve phrases from database"}), 500


# Add a new Phrase
@routes_bp.route("/phrases", methods=["POST"])
def add_phrase():
    """Adds a new phrase triplet to the database."""
    data = request.json
    if not data or 'SylhetiText' not in data or 'BengaliText' not in data or 'EnglishText' not in data:
        return jsonify({"error": "Missing required fields (SylhetiText, BengaliText, EnglishText)"}), 400

    try:
        new_phrase = Phrase(
            SylhetiText=data["SylhetiText"], BengaliText=data["BengaliText"], EnglishText=data["EnglishText"]
        )
        db.session.add(new_phrase)
        db.session.commit()
        return jsonify({"message": "Phrase added Successfully", "PhraseID": new_phrase.PhraseID}), 201
    except Exception as e:
         print(f"Error adding phrase: {e}")
         db.session.rollback() # Rollback in case of error
         return jsonify({"error": "Could not add phrase to database"}), 500


# Delete a Phrase
@routes_bp.route("/phrases/<int:id>", methods=["DELETE"])
def delete_phrases(id):
    """Deletes a phrase by its ID."""
    try:
        phrase = Phrase.query.get_or_404(id) # Use get_or_404 for cleaner error handling
        db.session.delete(phrase)
        db.session.commit()
        return jsonify({"message": "Phrase Deleted Successfully"})
    except Exception as e:
         print(f"Error deleting phrase {id}: {e}")
         db.session.rollback()
         # get_or_404 already handles Not Found, so this is likely a DB error
         return jsonify({"error": f"Could not delete phrase {id}"}), 500


# Add a new Speaker
@routes_bp.route("/speakers", methods=["POST"])
def add_speaker():
    """Adds a new speaker to the database."""
    data = request.json
    if not data or 'Name' not in data or 'Gender' not in data:
         return jsonify({"error": "Missing required fields for Speaker (Name, Gender)"}), 400
    # Add validation for Gender enum if needed from your model definition
    allowed_genders = ['Male', 'Female', 'Other'] # Or get from model config
    if data['Gender'] not in allowed_genders:
         return jsonify({"error": f"Invalid Gender specified. Must be one of: {allowed_genders}"}), 400

    try:
        new_speaker = Speaker(Name=data["Name"], Gender=data["Gender"], Region=data.get("Region")) # Allow null Region
        db.session.add(new_speaker)
        db.session.commit()
        return jsonify({"message": "Speaker added Successfully", "SpeakerID": new_speaker.SpeakerID}), 201
    except Exception as e:
        print(f"Error adding speaker: {e}")
        db.session.rollback()
        return jsonify({"error": "Could not add speaker to database"}), 500


# Get all Speakers
@routes_bp.route("/speakers", methods=["GET"])
def get_speakers():
    """Returns all speakers currently in the database."""
    try:
        speakers = Speaker.query.all()
        return jsonify([
            {"SpeakerID": s.SpeakerID, "Name": s.Name, "Gender": s.Gender, "Region": s.Region}
            for s in speakers
        ])
    except Exception as e:
        print(f"Error fetching speakers: {e}")
        return jsonify({"error": "Could not retrieve speakers from database"}), 500


# Add an Audio File Entry
@routes_bp.route("/audio", methods=["POST"])
def add_audio():
    """Adds a new audio file reference to the database."""
    data = request.json
    if not data or 'PhraseID' not in data or 'SpeakerID' not in data:
         return jsonify({"error": "Missing required fields for AudioFile (PhraseID, SpeakerID)"}), 400

    try:
        # Optional: Check if PhraseID and SpeakerID actually exist?
        # phrase_exists = db.session.query(Phrase.PhraseID).filter_by(PhraseID=data["PhraseID"]).scalar() is not None
        # speaker_exists = db.session.query(Speaker.SpeakerID).filter_by(SpeakerID=data["SpeakerID"]).scalar() is not None
        # if not phrase_exists or not speaker_exists:
        #     return jsonify({"error": "Specified PhraseID or SpeakerID does not exist"}), 404

        new_audio = AudioFile(PhraseID=data["PhraseID"], SpeakerID=data["SpeakerID"], FilePath=data.get("FilePath")) # Allow null FilePath initially
        db.session.add(new_audio)
        db.session.commit()
        return jsonify({"message": "Audio entry added Successfully", "AudioFileID": new_audio.AudioFileID}), 201
    except Exception as e:
         print(f"Error adding audio entry: {e}")
         db.session.rollback()
         # Could be foreign key constraint error if IDs don't exist
         return jsonify({"error": "Could not add audio entry to database (check PhraseID/SpeakerID validity)"}), 500


# Get all Audio Files
@routes_bp.route("/audio", methods=["GET"])
def get_audio():
    """Returns all audio file references currently in the database."""
    try:
        audio_files = AudioFile.query.all()
        return jsonify([
            {"AudioFileID": a.AudioFileID, "PhraseID": a.PhraseID, "SpeakerID": a.SpeakerID, "FilePath": a.FilePath}
            for a in audio_files
        ])
    except Exception as e:
        print(f"Error fetching audio entries: {e}")
        return jsonify({"error": "Could not retrieve audio entries from database"}), 500