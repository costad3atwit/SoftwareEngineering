from __future__ import annotations
from typing import List
from enums import Color, PieceType
from coordinate import Coordinate
from move import Move

class Piece:
    def __init__(self, id: str, color: Color, piece_type: PieceType):
        self.id = id
        self.color = color
        self.type = piece_type
        self.has_moved = False

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        """Return a list of legal moves for this piece."""
        raise NotImplementedError()

    def clone(self) -> 'Piece':
        """Return a deep copy of the piece."""
        return Piece(self.id, self.color, self.type)
    
    def algebraic_notation(self) -> str:
        """Return the algebraic notation for the piece."""
        return self.type.value
    
    def __str__(self):
        """Return the name, type, and id of the piece"""
        return f"{self.color.value} {self.type.value.capitalize()} ({self.id})"


class King(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.KING)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return []  # implement later


class Queen(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.QUEEN)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class Rook(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.ROOK)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class Bishop(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.BISHOP)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        moves: List[Move] = []

        # four diagonal directions: (file, rank)
        directions = [
            (1, 1),   # up-right
            (1, -1),  # down-right
            (-1, 1),  # up-left
            (-1, -1)  # down-left
        ]

        for df, dr in directions:
            next_coord = at.offset(df, dr)
            while next_coord:
                # empty square: can move and continue
                if board.is_empty(next_coord):
                    moves.append(Move(at, next_coord))
                # enemy piece: can capture, but stop moving further
                elif board.is_enemy(next_coord, self.color):
                    moves.append(Move(at, next_coord))
                    break
                # friendly piece: cannot move past or capture
                else:
                    break

                # Continue in the same direction
                next_coord = next_coord.offset(df, dr)

        return moves


class Knight(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.KNIGHT)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class Pawn(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.PAWN)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        """
        Generate all legal moves for this pawn given the current board state.
        board is expected to provide:
            - is_empty(square: Coordinate) -> bool
            - get_piece(square: Coordinate) -> Optional[Piece]
        """
        legal_moves = []
        direction = 1 if self.color == "white" else -1  # White moves up, black moves down

        # --- Forward move (1 square) ---
        one_step = Coordinate(self.at.file, self.at.rank + direction)
        if board.is_empty(one_step):
            legal_moves.append(Move(self.at, one_step))

            # --- Forward move (2 squares on first move) ---
            if not self.has_moved:
                two_step = Coordinate(self.at.file, self.at.rank + 2 * direction)
                if board.is_empty(two_step):
                    legal_moves.append(Move(self.at, two_step))

        # --- Captures (diagonals) ---
        for file_offset in [-1, 1]:
            capture_sq = Coordinate(self.at.file + file_offset, self.at.rank + direction)
            if board.is_within_bounds(capture_sq):
                target_piece = board.get_piece(capture_sq)
                if target_piece and target_piece.color != self.color:
                    legal_moves.append(Move(self.at, capture_sq))

        # --- Promotion check ---
        promotion_rank = 7 if self.color == "white" else 0
        for move in legal_moves:
            if move.to_sq.rank == promotion_rank:
                move.promotion = "Queen"  # default promotion, can be changed by player

        return legal_moves
     def has_moved(self) -> bool:
         self.has_moved = True


class Peon(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.PEON)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class Scout(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.SCOUT)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class HeadHunter(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.HEADHUNTER)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class Witch(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.WITCH)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class Warlock(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.WARLOCK)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class Cleric(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.CLERIC)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class DarkLord(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.DARKLORD)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later
