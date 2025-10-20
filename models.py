from db_config import db
from datetime import datetime

class TextRecord(db.Model):
    __tablename__ = 'text_records_rows'
    id = db.Column(db.String(50), primary_key=True)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.String, nullable=False)
    source = db.Column(db.String)
    word_count = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Word(db.Model):
    __tablename__ = 'words_rows'
    id = db.Column(db.String, primary_key=True)
    word = db.Column(db.String, nullable=False)
    meaning = db.Column(db.String, nullable=False)
    is_learned = db.Column(db.Boolean, default=False)
    text_id = db.Column(db.String)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
