from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager, utc_now

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    hosted_auctions = db.relationship("AuctionRoom", back_populates="host", foreign_keys="AuctionRoom.host_id", cascade="all, delete-orphan")
    teams = db.relationship("Team", back_populates="owner", cascade="all, delete-orphan")
    bids = db.relationship("Bid", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, username=None, email=None, password=None, password_hash=None, **kwargs):
        super().__init__(username=username, email=email, password_hash=password_hash, **kwargs)
        if password:
            self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        return None
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None
