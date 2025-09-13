from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    intended_use = db.Column(db.String(200))
    target_audience = db.Column(db.String(200))
    expected_outcome = db.Column(db.String(200))
    tags = db.Column(db.String(200)) # Simple comma-separated string for now
    is_shared = db.Column(db.Boolean, default=False, nullable=False)
    generated_prompts = db.relationship('GeneratedPrompt', backref='prompt', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'intended_use': self.intended_use,
            'target_audience': self.target_audience,
            'expected_outcome': self.expected_outcome,
            'tags': self.tags,
            'is_shared': self.is_shared,
        }

class GeneratedPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    generated_text = db.Column(db.Text, nullable=False)
    prompt_token_count = db.Column(db.Integer)
    candidates_token_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'prompt_id': self.prompt_id,
            'generated_text': self.generated_text,
            'prompt_token_count': self.prompt_token_count,
            'candidates_token_count': self.candidates_token_count,
            'created_at': self.created_at.isoformat()
        }
