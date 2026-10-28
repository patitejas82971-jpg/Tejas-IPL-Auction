from app.extensions import db, utc_now
from app.models.player import format_inr

class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey("auction_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_name = db.Column(db.String(64), nullable=False)
    team_code = db.Column(db.String(10), nullable=False)  # CSK, MI, etc.
    short_name = db.Column(db.String(32), default="")
    primary_color = db.Column(db.String(16), default="#F5B841")
    secondary_color = db.Column(db.String(16), default="#071A36")
    text_color = db.Column(db.String(16), default="#FFFFFF")
    logo_icon = db.Column(db.String(64), default="fa-shield-halved")
    starting_budget = db.Column(db.BigInteger, nullable=False, default=1200000000)
    remaining_budget = db.Column(db.BigInteger, nullable=False, default=1200000000)
    is_ready = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    owner = db.relationship("User", back_populates="teams")
    auction = db.relationship("AuctionRoom", back_populates="teams", foreign_keys=[auction_id])
    squad_entries = db.relationship("TeamSquad", back_populates="team", cascade="all, delete-orphan", lazy="joined")
    bids = db.relationship("Bid", back_populates="team", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("auction_id", "team_code", name="unique_team_per_auction"),
        db.UniqueConstraint("auction_id", "owner_id", name="unique_owner_per_auction"),
    )

    @property
    def spent_budget(self):
        return max(0, self.starting_budget - self.remaining_budget)

    @property
    def squad_count(self):
        return len(self.squad_entries)

    @property
    def overseas_count(self):
        return sum(1 for entry in self.squad_entries if entry.player and entry.player.is_overseas)

    def get_role_distribution(self):
        roles = {"Batsman": 0, "Bowler": 0, "All-rounder": 0, "Wicketkeeper": 0}
        for entry in self.squad_entries:
            if entry.player:
                roles[entry.player.role] = roles.get(entry.player.role, 0) + 1
        return roles

    def to_dict(self, include_squad=False):
        data = {
            "id": self.id,
            "auction_id": self.auction_id,
            "owner_id": self.owner_id,
            "owner_name": self.owner.username if self.owner else "Unknown",
            "team_name": self.team_name,
            "team_code": self.team_code,
            "short_name": self.short_name,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "text_color": self.text_color,
            "logo_icon": self.logo_icon,
            "starting_budget": self.starting_budget,
            "starting_budget_formatted": format_inr(self.starting_budget),
            "remaining_budget": self.remaining_budget,
            "remaining_budget_formatted": format_inr(self.remaining_budget),
            "spent_budget": self.spent_budget,
            "spent_budget_formatted": format_inr(self.spent_budget),
            "is_ready": self.is_ready,
            "squad_count": self.squad_count,
            "overseas_count": self.overseas_count,
            "roles": self.get_role_distribution()
        }
        if include_squad:
            data["squad"] = [entry.to_dict() for entry in self.squad_entries]
        return data

    def __repr__(self):
        return f"<Team {self.team_code} - {self.team_name}>"


class TeamSquad(db.Model):
    __tablename__ = "team_squads"

    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey("auction_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    purchase_price = db.Column(db.BigInteger, nullable=False)
    acquired_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    team = db.relationship("Team", back_populates="squad_entries")
    player = db.relationship("Player", back_populates="squad_entries", lazy="joined")
    auction = db.relationship("AuctionRoom", back_populates="squad_entries")

    __table_args__ = (
        db.UniqueConstraint("auction_id", "player_id", name="unique_player_sale_per_auction"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "auction_id": self.auction_id,
            "team_id": self.team_id,
            "player_id": self.player_id,
            "player": self.player.to_dict() if self.player else None,
            "purchase_price": self.purchase_price,
            "purchase_price_formatted": format_inr(self.purchase_price),
            "acquired_at": self.acquired_at.isoformat() if self.acquired_at else None
        }

    def __repr__(self):
        return f"<TeamSquad Team:{self.team_id} Player:{self.player_id}>"
