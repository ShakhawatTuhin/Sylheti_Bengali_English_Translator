# models.py
print("--- models.py: STARTING TO LOAD (FULL VERSION) ---")

from config import db

print(f"--- models.py: 'db' object imported from config. ID: {id(db)} ---")

class Phrase(db.Model):
    print("--- models.py: Defining Phrase model ---")
    __tablename__  = 'phrases'
    PhraseID = db.Column(db.Integer, primary_key=True)
    SylhetiText = db.Column(db.Text, nullable=False)
    BengaliText = db.Column(db.Text, nullable=False)
    EnglishText = db.Column(db.Text, nullable=True)
    audio_files = db.relationship('AudioFile', backref='phrase', lazy=True, cascade="all, delete-orphan")

class Speaker(db.Model):
    print("--- models.py: Defining Speaker model ---")
    __tablename__ = 'speakers'
    SpeakerID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100))
    Gender = db.Column(db.Enum('Male', 'Female', 'Other', name='gender_enum_type'), nullable=False)
    Region = db.Column(db.String(100))
    audio_files = db.relationship('AudioFile', backref='speaker', lazy=True)

class AudioFile(db.Model):
    print("--- models.py: Defining AudioFile model ---")
    __tablename__ = 'audio_files'
    AudioFileID = db.Column(db.Integer, primary_key=True)
    FilePath = db.Column(db.String(500), nullable=True, unique=True)
    DurationSeconds = db.Column(db.Float, nullable=True)
    SampleRate = db.Column(db.Integer, nullable=True)
    PhraseID = db.Column(db.Integer, db.ForeignKey('phrases.PhraseID', ondelete='CASCADE'), nullable=False, index=True)
    SpeakerID = db.Column(db.Integer, db.ForeignKey('speakers.SpeakerID'), nullable=False, index=True)

print("--- models.py: FINISHED LOADING (FULL VERSION) ---")
