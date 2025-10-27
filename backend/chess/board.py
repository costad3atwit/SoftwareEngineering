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
        self.dmzActive = False

    def dmz_Activate():
        """
        Help change the set up of board to 10x10
        by changing dmzActive to True
        """
        self.dmzActive = True
    
    def setup_standard(self):
        """Set up standard chessboard layout."""
        self.squares.clear() # clear board

        # for file positions (a–j)
        files = range(10)

        # Place Pawns
        for file in files:
            if(file == 0 or file == 9):
                continue
            self.squares[Coordinate(file, 2)] = Pawn(f"wP{file}", Color.WHITE)
            self.squares[Coordinate(file, 7)] = Pawn(f"bP{file}", Color.BLACK)

        # Place Rooks
        self.squares[Coordinate(1, 1)] = Rook("wR1", Color.WHITE)
        self.squares[Coordinate(8, 1)] = Rook("wR2", Color.WHITE)
        self.squares[Coordinate(1, 8)] = Rook("bR1", Color.BLACK)
        self.squares[Coordinate(8, 8)] = Rook("bR2", Color.BLACK)

        # Place Knights
        self.squares[Coordinate(2, 1)] = Knight("wN1", Color.WHITE)
        self.squares[Coordinate(7, 1)] = Knight("wN2", Color.WHITE)
        self.squares[Coordinate(2, 8)] = Knight("bN1", Color.BLACK)
        self.squares[Coordinate(7, 8)] = Knight("bN2", Color.BLACK)

        # Place Bishops
        self.squares[Coordinate(3, 1)] = Bishop("wB1", Color.WHITE)
        self.squares[Coordinate(6, 1)] = Bishop("wB2", Color.WHITE)
        self.squares[Coordinate(3, 8)] = Bishop("bB1", Color.BLACK)
        self.squares[Coordinate(6, 8)] = Bishop("bB2", Color.BLACK)

        # Place Queens
        self.squares[Coordinate(4, 1)] = Queen("wQ", Color.WHITE)
        self.squares[Coordinate(4, 8)] = Queen("bQ", Color.BLACK)

        # Place Kings
        self.squares[Coordinate(5, 1)] = King("wK", Color.WHITE)
        self.squares[Coordinate(5, 8)] = King("bK", Color.BLACK)

    def piece_at_coord(self, coord: Coordinate) -> Optional[Piece]:
        """Get coordinates of piece on the board"""
        return self.squares.get(coord)

    def is_in_bounds(self, coord: Coordinate) -> bool:
        """
        Check if the given coordinate is within the boundaries of the board.
        """
        if(self.dmzActive):
            return 0 <= coord.file <= 9 and 0 <= coord.rank <= 9
        else:
            return 1 <= coord.file <= 8 and 1 <= coord.rank <= 8

    def is_empty(self, coord: Coordinate) -> bool:
        """Return True if the given coordinate has no piece."""
        if(self.is_in_bounds(coord)):
            return coord not in self.squares
        else:
            raise ValueError("Invalid Coordinate")

    def is_enemy(self, coord: Coordinate, color: Color) -> bool:
        """Return True if the coordinate contains an enemy piece."""
        if(self.is_in_bounds(coord)):
            piece = self.squares.get(coord)
            return piece is not None and piece.color != color
        else:
            raise ValueError("Invalid Coordinate")

    def is_frendly(self, coord: Coordinate, color: Color) -> bool:
        """Return True if the coordinate contains an enemy piece."""
        if(self.is_in_bounds(coord)):
            piece = self.squares.get(coord)
            return piece is not None and piece.color == color
        else:
            raise ValueError("Invalid Coordinate")
    
    def move_piece(self, move: Move) -> Optional[Piece]:
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
                for move in piece.get_legal_captures(self, coord):
                    if move.to_coord == king_coord:
                        return True
        return False

    def clone(self) -> 'Board':
        """Return a deep copy of the board."""
        new_board = Board()
        new_board.squares = {coord: copy.deepcopy(piece) for coord, piece in self.squares.items()}
        return new_board
