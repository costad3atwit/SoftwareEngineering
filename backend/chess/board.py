from __future__ import annotations
from typing import Dict, Optional
from coordinate import Coordinate
from piece import Piece, King, Queen, Rook, Bishop, Knight, Pawn
from move import Move
from enums import Color
import copy

class Board:
    def __init__(self):
        self.squares: Dict[Coordinate, Piece] = {}

    def setup_standard(self):
        """Set up standard chessboard layout."""
        self.squares.clear() # clear board

        # for file positions (a–h)
        # will change later for card effect
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
    
    def is_empty(self, coord: Coordinate) -> bool:
        """Return True if the given coordinate has no piece."""
        return coord not in self.squares

    def is_enemy(self, coord: Coordinate, color: Color) -> bool:
        """Return True if the coordinate contains an enemy piece."""
        piece = self.squares.get(coord)
        return piece is not None and piece.color != color
    
    def move_piece(self, move: Move) -> None:
        """Move a piece from one coordinate to another. Return captured piece if any."""
        src = move.from_coord
        dest = move.to_coord

        moving_piece = self.squares.get(src)
        if not moving_piece:
            raise ValueError(f"No piece at {src}")

        # capture if needed
        captured_piece = self.squares.pop(dest, None)

        # perform the move
        self.squares.pop(src)
        self.squares[dest] = moving_piece
        moving_piece.has_moved = True

        return captured_piece

    def in_check_for(self, color: Color) -> bool:
        """Return True if the given color's King is under attack."""
        # find the king’s position
        king_coord = None
        for coord, piece in self.squares.items():
            if isinstance(piece, King) and piece.color == color:
                king_coord = coord
                break

        if not king_coord:
            return False  # no king found (invalid board state)

        # check if any opposing piece can move to king’s coordinate
        for coord, piece in self.squares.items():
            if piece.color != color:
                for move in piece.get_legal_moves(self, coord):
                    if move.to_coord == king_coord:
                        return True
        return False

    def clone(self) -> 'Board':
        """Return a deep copy of the board."""
        new_board = Board()
        new_board.squares = {coord: copy.deepcopy(piece) for coord, piece in self.squares.items()}
        return new_board
