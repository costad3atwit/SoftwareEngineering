from typing import List, Optional
from backend.chess.coordinate import Coordinate
from backend.chess.move import Move
from backend.chess.piece import Piece


class Pawn(Piece):
    def __init__(self, color: str, position: Coordinate):
        super().__init__(color, position)

    def get_legal_moves(self, board) -> List[Move]:
        """
        Generate all legal moves for this pawn given the current board state.
        board is expected to provide:
            - is_empty(square: Coordinate) -> bool
            - get_piece(square: Coordinate) -> Optional[Piece]
        """
        legal_moves = []
        direction = 1 if self.color == "white" else -1  # White moves up, black moves down

        # --- Forward move (1 square) ---
        one_step = Coordinate(self.position.file, self.position.rank + direction)
        if board.is_empty(one_step):
            legal_moves.append(Move(self.position, one_step))

            # --- Forward move (2 squares on first move) ---
            if not self.has_moved:
                two_step = Coordinate(self.position.file, self.position.rank + 2 * direction)
                if board.is_empty(two_step):
                    legal_moves.append(Move(self.position, two_step))

        # --- Captures (diagonals) ---
        for file_offset in [-1, 1]:
            capture_sq = Coordinate(self.position.file + file_offset, self.position.rank + direction)
            if board.is_within_bounds(capture_sq):
                target_piece = board.get_piece(capture_sq)
                if target_piece and target_piece.color != self.color:
                    legal_moves.append(Move(self.position, capture_sq))

        # --- Promotion check ---
        promotion_rank = 7 if self.color == "white" else 0
        for move in legal_moves:
            if move.to_sq.rank == promotion_rank:
                move.promotion = "Queen"  # default promotion, can be changed by player

        return legal_moves

    def __str__(self):
        return f"{'White' if self.color == 'white' else 'Black'} Pawn at {self.position}"
