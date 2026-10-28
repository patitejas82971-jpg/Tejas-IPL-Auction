import json
from app.extensions import db, utc_now
from app.models.player import format_inr

class AuctionRoom(db.Model):
    __tablename__ = "auction_rooms"

    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    room_name = db.Column(db.String(128), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(20), default="lobby", index=True)  # lobby, active, paused, completed
    auction_type = db.Column(db.String(20), default="mega")  # mega, mini, custom
    starting_budget = db.Column(db.BigInteger, default=1200000000)
    max_teams = db.Column(db.Integer, default=10)
    squad_rules = db.Column(db.Text, default="{}")
    
    # Active auction state
    current_player_id = db.Column(db.Integer, db.ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    current_highest_bid = db.Column(db.BigInteger, default=0)
    current_highest_team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="SET NULL", use_alter=True, name="fk_auction_highest_team"), nullable=True)
    bid_deadline = db.Column(db.DateTime, nullable=True)
    timer_paused_remaining = db.Column(db.Integer, default=30)
    
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    host = db.relationship("User", back_populates="hosted_auctions", foreign_keys=[host_id])
    teams = db.relationship("Team", back_populates="auction", cascade="all, delete-orphan", foreign_keys="Team.auction_id")
    auction_players = db.relationship("AuctionPlayer", back_populates="auction", cascade="all, delete-orphan", order_by="AuctionPlayer.order_index")
    squad_entries = db.relationship("TeamSquad", back_populates="auction", cascade="all, delete-orphan")
    bids = db.relationship("Bid", back_populates="auction", cascade="all, delete-orphan")
    events = db.relationship("AuctionEvent", back_populates="auction", cascade="all, delete-orphan", order_by="AuctionEvent.id.desc()")
    
    current_player = db.relationship("Player", foreign_keys=[current_player_id])
    highest_bidding_team = db.relationship("Team", foreign_keys=[current_highest_team_id])

    def get_rules(self):
        try:
            return json.loads(self.squad_rules)
        except Exception:
            return {
                "min_squad_size": 18,
                "max_squad_size": 25,
                "max_overseas": 8,
                "timer_duration": 30,
                "timer_extend_seconds": 15
            }

    def set_rules(self, rules_dict):
        self.squad_rules = json.dumps(rules_dict)

    def to_dict(self, full=False):
        rules = self.get_rules()
        data = {
            "id": self.id,
            "room_code": self.room_code,
            "room_name": self.room_name,
            "host_id": self.host_id,
            "host_name": self.host.username if self.host else "Host",
            "status": self.status,
            "auction_type": self.auction_type,
            "starting_budget": self.starting_budget,
            "starting_budget_formatted": format_inr(self.starting_budget),
            "max_teams": self.max_teams,
            "current_teams_count": len(self.teams),
            "rules": rules,
            "current_player_id": self.current_player_id,
            "current_highest_bid": self.current_highest_bid,
            "current_highest_bid_formatted": format_inr(self.current_highest_bid),
            "current_highest_team_id": self.current_highest_team_id,
            "highest_bidding_team": self.highest_bidding_team.to_dict() if self.highest_bidding_team else None,
            "bid_deadline": self.bid_deadline.isoformat() if self.bid_deadline else None,
            "timer_paused_remaining": self.timer_paused_remaining,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if self.current_player:
            data["current_player"] = self.current_player.to_dict()
        else:
            data["current_player"] = None

        if full:
            data["teams"] = [t.to_dict(include_squad=True) for t in self.teams]
            data["total_players"] = len(self.auction_players)
            data["sold_players_count"] = sum(1 for ap in self.auction_players if ap.status == "sold")
            data["unsold_players_count"] = sum(1 for ap in self.auction_players if ap.status == "unsold")
            data["pending_players_count"] = sum(1 for ap in self.auction_players if ap.status == "pending")

        return data

    def __repr__(self):
        return f"<AuctionRoom {self.room_code} - {self.room_name}>"


class AuctionPlayer(db.Model):
    __tablename__ = "auction_players"

    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey("auction_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(20), default="pending", index=True)  # pending, current, sold, unsold
    sold_price = db.Column(db.BigInteger, default=0)
    winning_team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    order_index = db.Column(db.Integer, default=0, index=True)
    pool = db.Column(db.String(32), default="", index=True)
    set_name = db.Column(db.String(64), default="", index=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    auction = db.relationship("AuctionRoom", back_populates="auction_players")
    player = db.relationship("Player", back_populates="auction_entries", lazy="joined")
    winning_team = db.relationship("Team", foreign_keys=[winning_team_id])

    __table_args__ = (
        db.UniqueConstraint("auction_id", "player_id", name="unique_player_per_auction"),
    )

    def to_dict(self):
        p_dict = self.player.to_dict() if self.player else None
        return {
            "id": self.id,
            "auction_id": self.auction_id,
            "player_id": self.player_id,
            "player": p_dict,
            "status": self.status,
            "sold_price": self.sold_price,
            "sold_price_formatted": format_inr(self.sold_price) if self.sold_price else "₹0",
            "winning_team_id": self.winning_team_id,
            "winning_team": self.winning_team.to_dict() if self.winning_team else None,
            "order_index": self.order_index,
            "pool": self.pool or (p_dict["pool"] if p_dict else ""),
            "set_name": self.set_name or (p_dict["set_name"] if p_dict else "")
        }

    def __repr__(self):
        return f"<AuctionPlayer Auction:{self.auction_id} Player:{self.player_id} Status:{self.status}>"
