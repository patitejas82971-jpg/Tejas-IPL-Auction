from app.extensions import db, utc_now

def format_inr(amount):
    """Format amount in INR Crores or Lakhs."""
    if amount is None:
        return "₹0"
    amt = float(amount)
    if amt >= 10000000:
        cr = amt / 10000000
        return f"₹{cr:.2f}".rstrip("0").rstrip(".") + " Cr"
    elif amt >= 100000:
        lakh = amt / 100000
        return f"₹{lakh:.2f}".rstrip("0").rstrip(".") + " Lakh"
    else:
        return f"₹{int(amt):,}"

class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    country = db.Column(db.String(64), nullable=False, index=True)
    role = db.Column(db.String(32), nullable=False, index=True)  # Batsman, Bowler, All-rounder, Wicketkeeper
    batting_style = db.Column(db.String(64), default="Right Handed")
    bowling_style = db.Column(db.String(64), default="None")
    base_price = db.Column(db.BigInteger, nullable=False, default=20000000)
    is_overseas = db.Column(db.Boolean, default=False, index=True)
    is_uncapped = db.Column(db.Boolean, default=False, index=True)
    image_url = db.Column(db.String(512), default="")
    rating = db.Column(db.Integer, default=80)
    pool = db.Column(db.String(32), default="Capped", index=True)  # Marquee, Capped, Uncapped
    is_marquee = db.Column(db.Boolean, default=False, index=True)
    set_name = db.Column(db.String(64), default="", index=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    auction_entries = db.relationship("AuctionPlayer", back_populates="player", cascade="all, delete-orphan")
    squad_entries = db.relationship("TeamSquad", back_populates="player", cascade="all, delete-orphan")
    bids = db.relationship("Bid", back_populates="player", cascade="all, delete-orphan")

    def to_dict(self):
        computed_pool = self.pool or ("Marquee" if (self.is_marquee or (not self.is_uncapped and (self.rating or 0) >= 93)) else ("Uncapped" if self.is_uncapped else "Capped"))
        plural = "Batsmen" if self.role == "Batsman" else ("Bowlers" if self.role == "Bowler" else ("All-rounders" if self.role == "All-rounder" else "Wicketkeepers"))
        computed_set = self.set_name or f"{computed_pool} {plural}"
        return {
            "id": self.id,
            "player_id": self.id,
            "name": self.name,
            "country": self.country,
            "role": self.role,
            "batting_style": self.batting_style,
            "bowling_style": self.bowling_style,
            "base_price": self.base_price,
            "base_price_formatted": format_inr(self.base_price),
            "is_overseas": self.is_overseas,
            "is_uncapped": self.is_uncapped,
            "pool": computed_pool,
            "is_marquee": bool(self.is_marquee or computed_pool == "Marquee"),
            "set_name": computed_set,
            "image_url": self.image_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={self.name.replace(' ', '_')}&backgroundColor=071a36",
            "rating": self.rating
        }

    def __repr__(self):
        return f"<Player {self.name} - {self.role}>"
