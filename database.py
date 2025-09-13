from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True, nullable=False)
    gender = db.Column(db.String(10))
    prompts = db.relationship('Prompt', backref='author', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), default='', nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    intended_use = db.Column(db.String(200))
    target_audience = db.Column(db.String(200))
    expected_outcome = db.Column(db.String(200))
    tags = db.Column(db.String(200)) # Simple comma-separated string for now
    is_shared = db.Column(db.Boolean, default=False, nullable=False)
    generated_prompts = db.relationship('GeneratedPrompt', backref='prompt', lazy=True, cascade="all, delete-orphan")
    votes = db.relationship('PromptVote', backref='prompt', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        upvotes = sum(1 for v in self.votes if v.vote == 1)
        downvotes = sum(1 for v in self.votes if v.vote == -1)
        return {
            'id': self.id,
            'author': self.author.username,
            'title': self.title,
            'text': self.text,
            'intended_use': self.intended_use,
            'target_audience': self.target_audience,
            'expected_outcome': self.expected_outcome,
            'tags': self.tags,
            'is_shared': self.is_shared,
            'created_at': self.created_at.isoformat(),
            'upvotes': upvotes,
            'downvotes': downvotes
        }

class PromptVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    vote = db.Column(db.Integer, nullable=False)  # 1 for upvote, -1 for downvote
    __table_args__ = (db.UniqueConstraint('user_id', 'prompt_id', name='_user_prompt_uc'),)


class GeneratedPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=False)
    generated_text = db.Column(db.Text, nullable=False)
    
    # Prompt analysis fields
    overall_score = db.Column(db.Integer)
    clarity = db.Column(db.Integer)
    specificity = db.Column(db.Integer)
    effectiveness = db.Column(db.Integer)
    refined_prompt = db.Column(db.Text)
    improvements_made = db.Column(db.JSON)
    additional_suggestions = db.Column(db.JSON)

    prompt_token_count = db.Column(db.Integer)
    candidates_token_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'prompt_id': self.prompt_id,
            'generated_text': self.generated_text,
            'analysis': {
                'overall_score': self.overall_score,
                'clarity': self.clarity,
                'specificity': self.specificity,
                'effectiveness': self.effectiveness,
                'refined_prompt': self.refined_prompt,
                'improvements_made': self.improvements_made,
                'additional_suggestions': self.additional_suggestions,
            },
            'usage_metadata': {
                'prompt_token_count': self.prompt_token_count,
                'candidates_token_count': self.candidates_token_count,
            },
            'created_at': self.created_at.isoformat()
        }

class TokenBlacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<TokenBlacklist {self.jti}>"
