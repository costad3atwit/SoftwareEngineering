from coordinate import Coordinate
from piece import Piece
from move import Move
from enums import Color
from typing import Dict

class Board:
    def __init__(self):
        self.squares: Dict[Coordinate, Piece] = {}

    def setup_standard(self):
        """Set up standard chessboard layout."""
        self.squares.clear() # clear board

        # for file positions (a–h)
        files = range(8)

        # Place Pawns
        for file in files:
            self.squares[Coordinate(file, 1)] = Pawn(f"wP{file}", Color.WHITE)
            self.squares[Coordinate(file, 6)] = Pawn(f"bP{file}", Color.BLACK)

        # Place Rooks
        self.squares[Coordinate(0, 0)] = Rook("wR1", Color.WHITE)
        self.squares[Coordinate(7, 0)] = Rook("wR2", Color.WHITE)
        self.squares[Coordinate(0, 7)] = Rook("bR1", Color.BLACK)
        self.squares[Coordinate(7, 7)] = Rook("bR2", Color.BLACK)

        # Place Knights
        self.squares[Coordinate(1, 0)] = Knight("wN1", Color.WHITE)
        self.squares[Coordinate(6, 0)] = Knight("wN2", Color.WHITE)
        self.squares[Coordinate(1, 7)] = Knight("bN1", Color.BLACK)
        self.squares[Coordinate(6, 7)] = Knight("bN2", Color.BLACK)

        # Place Bishops
        self.squares[Coordinate(2, 0)] = Bishop("wB1", Color.WHITE)
        self.squares[Coordinate(5, 0)] = Bishop("wB2", Color.WHITE)
        self.squares[Coordinate(2, 7)] = Bishop("bB1", Color.BLACK)
        self.squares[Coordinate(5, 7)] = Bishop("bB2", Color.BLACK)

        # Place Queens
        self.squares[Coordinate(3, 0)] = Queen("wQ", Color.WHITE)
        self.squares[Coordinate(3, 7)] = Queen("bQ", Color.BLACK)

        # Place Kings
        self.squares[Coordinate(4, 0)] = King("wK", Color.WHITE)
        self.squares[Coordinate(4, 7)] = King("bK", Color.BLACK)

    def piece_at_coord(self, coord: Coordinate) -> Piece:
        """Get coordinates of piece on the board"""
        return self.squares.get(coord)

    def move_piece(self, move: Move) -> None:
        """Move a piece from one coordinate to another."""
        pass # implement later

    def in_check_for(self, color: Color) -> bool:
        """Return true if the given color is in check."""
        return False # implement later

    def clone(self) -> 'Board':
        """Return a deep copy of the board."""
        cloned = Board() # implement later
        return cloned
