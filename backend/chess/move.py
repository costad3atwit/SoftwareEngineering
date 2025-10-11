class Move:
    def __init__(self, from_sq: Coordinate, to_sq: Coordinate, promotion=None, card_play_id=None, metadata=None):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.promotion = promotion
        self.card_play_id = card_play_id
        self.metadata = metadata
