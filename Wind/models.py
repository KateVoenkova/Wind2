from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    characters = db.relationship('Character', backref='book', lazy=True, cascade='all, delete-orphan')

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)  # Новое поле
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE'), nullable=False)

class CharacterRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character1_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    character2_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    weight = db.Column(db.Integer, default=1)

    __table_args__ = (
        db.UniqueConstraint('character1_id', 'character2_id', 'book_id', name='unique_relationship'),
    )