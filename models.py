from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(50), nullable=False)
    native_language = db.Column(db.String(50), nullable=False)
    learning_languages = db.Column(db.String(200))
    interests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    
    # Связи
    meetings = db.relationship('MeetingParticipant', backref='user', lazy=True)
    moderated_rooms = db.relationship('MeetingRoom', foreign_keys='MeetingRoom.moderator_id', backref='moderator')
    room_participations = db.relationship('RoomParticipant', backref='user_rel', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class Meeting(db.Model):
    __tablename__ = 'meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    topic = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    max_participants = db.Column(db.Integer, default=6)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=60)
    moderator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    participants = db.relationship('MeetingParticipant', backref='meeting', lazy=True)

class MeetingParticipant(db.Model):
    __tablename__ = 'meeting_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    rating = db.Column(db.Integer)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'meeting_id', name='unique_participation'),)

class MeetingRoom(db.Model):
    __tablename__ = 'meeting_rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    topic = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    max_participants = db.Column(db.Integer, default=6)
    current_participants = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    moderator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=60)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RoomParticipant(db.Model):
    __tablename__ = 'room_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('meeting_rooms.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    rating = db.Column(db.Integer)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', name='unique_room_participant'),)
    
    room = db.relationship('MeetingRoom', backref='participants_rel')