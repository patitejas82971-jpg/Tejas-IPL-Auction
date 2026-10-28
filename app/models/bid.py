import json
from app.extensions import db, utc_now
from app.models.player import format_inr

class Bid(db.Model):
    __tablename__ = "bids"

    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey("auction_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.BigInteger, nullable=False)
    timestamp = db.Column(db.DateTime, default=utc_now, index=True)

    # Relationships
    team = db.relationship("Team", back_populates="bids")
    user = db.relationship("User", back_populates="bids")
    player = db.relationship("Player", back_populates="bids")
    auction = db.relationship("AuctionRoom", back_populates="bids")

    def to_dict(self):
        return {
            "id": self.id,
            "auction_id": self.auction_id,
            "player_id": self.player_id,
            "team_id": self.team_id,
            "team_name": self.team.team_name if self.team else "Unknown Team",
            "team_code": self.team.team_code if self.team else "???",
            "primary_color": self.team.primary_color if self.team else "#F5B841",
            "user_id": self.user_id,
            "username": self.user.username if self.user else "User",
            "amount": self.amount,
            "amount_formatted": format_inr(self.amount),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self):
        return f"<Bid {self.team_id} {self.amount} on Player {self.player_id}>"


class AuctionEvent(db.Model):
    __tablename__ = "auction_events"

    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey("auction_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False)
    event_data = db.Column(db.Text, default="{}")
    timestamp = db.Column(db.DateTime, default=utc_now)

    # Relationships
    auction = db.relationship("AuctionRoom", back_populates="events")

    def set_data(self, data_dict):
        self.event_data = json.dumps(data_dict)

    def get_data(self):
        try:
            return json.loads(self.event_data)
        except Exception:
            return {}

    def to_dict(self):
        return {
            "id": self.id,
            "auction_id": self.auction_id,
            "event_type": self.event_type,
            "event_data": self.get_data(),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self):
        return f"<AuctionEvent {self.event_type} in Room {self.auction_id}>"
