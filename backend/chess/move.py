class Move:
    def __init__(self, from_sq: Coordinate, to_sq: Coordinate, promotion=None, card_play_id=None, metadata=None):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.promotion = promotion
        self.card_play_id = card_play_id
        self.metadata = metadata or {}

    def __str__(self):
        # Simple text version of the move 
        return f"Move from {self.from_sq} to {self.to_sq}" + (
            f" promoting to {self.promotion}" if self.promotion else ""
        )

    def to_dict(self):
        """Convert the move into a dictionary for logging"""
        return {
            "from_sq": {"file": self.from_sq.file, "rank": self.from_sq.rank},
            "to_sq": {"file": self.to_sq.file, "rank": self.to_sq.rank},
            "promotion": self.promotion,
            "card_play_id": self.card_play_id,
            "metadata": self.metadata
        }
