from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from backend.chess.coordinate import Coordinate

# Only import Piece for type checking, not at runtime
if TYPE_CHECKING:
    from backend.chess.piece import Piece
class Move:
    def __init__(self, from_sq: Coordinate, to_sq: Coordinate, piece: Piece,promotion: Piece =None, card_play_id=None, is_mark: bool = False, metadata=None):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.piece = piece
        self.promotion = promotion if promotion else None
        self.card_play_id = card_play_id
        self.is_mark = is_mark
        self.metadata = metadata or {}

    def __eq__(self, other):
        """Check if two moves are the same (ignoring piece object identity)"""
        if not isinstance(other, Move):
            return False
        return (self.from_sq == other.from_sq and 
                self.to_sq == other.to_sq and
                self.promotion == other.promotion and
                self.is_mark == other.is_mark)
    
    def __hash__(self):
        """Allow Move to be used in sets"""
        return hash((self.from_sq, self.to_sq, self.promotion))
    
    
    def __str__(self):
        # Simple text version of the move 
        return f"{self.piece.algebraic_notation()}{self.from_sq}->{self.to_sq}" + (
            f"={self.promotion.algebraic_notation}" if self.promotion else ""
        )

    def to_dict(self):
        """Convert the move into a dictionary for logging"""
        return {
            "from_sq": {"file": self.from_sq.file, "rank": self.from_sq.rank},
            "to_sq": {"file": self.to_sq.file, "rank": self.to_sq.rank},
            "promotion": self.promotion,
            "card_play_id": self.card_play_id,
            "is_mark": self.is_mark,
            "metadata": self.metadata
        }
