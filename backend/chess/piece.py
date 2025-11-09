from __future__ import annotations
from typing import List, Optional, Tuple, TYPE_CHECKING
from backend.enums import Color, PieceType
from backend.chess.coordinate import Coordinate
from backend.chess.move import Move
from abc import ABC, abstractmethod
from typing import Tuple

if TYPE_CHECKING:
    from backend.chess.board import Board

class Piece(ABC):
    def __init__(self, id: str, color: Color, piece_type: PieceType):
        self.id = id
        self.color = color
        self.type = piece_type
        self.has_moved = False
        self.marked = False
        self.piece_type = piece_type
        self.has_left_forbidden = False # For Forbidden Lands mechanic

    @abstractmethod
    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """Return a list of legal moves for this piece."""
        pass
        
    @abstractmethod
    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        """Return a list of legal captures for this piece."""
        pass
    
    def algebraic_notation(self) -> str:
        """Return the algebraic notation for the piece."""
        return self.type.value
    
    def __str__(self):
        """Return the name, type, and id of the piece"""
        return f"{self.color.value} {self.type.value.capitalize()} ({self.id})"

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:

        payload = {
            "id": self.id,
            "type": self.type.value,
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
            "marked": self.marked,
        }
        if include_moves and board is not None:
            moves = (self.get_legal_captures(board, at) if captures_only
                     else self.get_legal_moves(board, at))
            payload["moves"] = [{"from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                                 "to":   {"file": m.to_sq.file,   "rank": m.to_sq.rank}}
                                for m in moves]
        return payload




class King(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.KING)
        self._has_moved = False  # used for castling checks

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """All pseudo-legal king moves (no check filtering except for castling)."""
        moves: List[Move] = []

        # --- Normal king steps (8 directions) ---
        steps = [
            (-1, -1), (0, -1), (1, -1),
            (-1,  0),          (1,  0),
            (-1,  1), (0,  1), (1,  1),
        ]
        for dx, dy in steps:
            nf, nr = at.file + dx, at.rank + dy
            if not board.is_in_bounds(Coordinate(nf, nr)):
                continue
            
            # Prevent King from entering Forbidden Lands
            if getattr(board, "forbidden_active", False) and Coordinate(nf, nr) in getattr(board, "forbidden_positions", set()):
                continue

            target = board.piece_at_coord(Coordinate(nf, nr))
            # Can move if empty or capturing an opponent piece
            if target is None or target.color != self.color:
                dest = Coordinate(nf, nr)

                # If the Board exposes "is_square_attacked", disallow moving into check
                if hasattr(board, "is_square_attacked") and callable(getattr(board, "is_square_attacked")):
                    if board.is_square_attacked(dest, by_color=self._opponent_color()):
                        continue

                moves.append(Move(at, dest, self))

 
        if not self._has_moved:
            y = at.rank
            # Guard: only try castling if current square isn't attacked (when API exists)
            safe_to_try = True
            if hasattr(board, "is_square_attacked") and callable(getattr(board, "is_square_attacked")):
                if board.is_square_attacked(at, by_color=self._opponent_color()):
                    safe_to_try = False

            if safe_to_try:
                # King-side (toward file 7 rook): between squares are (at.file+1, y) and (at.file+2, y)
                self._try_castle(board, at, kingside=True, out_moves=moves)
                # Queen-side (toward file 0 rook): between squares are (at.file-1, y), (at.file-2, y), (at.file-3, y)
                self._try_castle(board, at, kingside=False, out_moves=moves)

        return moves

    def _try_castle(self, board: Board, at: Coordinate, kingside: bool, out_moves: List[Move]) -> None:
        """Attempt to add a castle move if all preconditions are satisfied."""
        # Determine rook file targets by side
        rook_file = 7 if kingside else 0
        y = at.rank

        # Rook must exist and be same color
        rook = board.piece_at_coord(Coordinate(rook_file, y))
        if rook is None or getattr(rook, "type", None) != PieceType.ROOK or rook.color != self.color:
            return

        # Rook must not have moved (expects rook._has_moved like King; skip if attribute absent)
        if getattr(rook, "_has_moved", False):
            return

        # Squares between king and rook must be empty
        if kingside:
            between_files = [at.file + 1, at.file + 2]
            landing_file = at.file + 2
            pass_through_files = [at.file + 1, at.file + 2]
        else:
            between_files = [at.file - 1, at.file - 2, at.file - 3]
            landing_file = at.file - 2
            pass_through_files = [at.file - 1, at.file - 2]

        for f in between_files:
            if not board.is_in_bounds(Coordinate(f, y)) or not board.is_empty(Coordinate(f, y)):
                return

        # Squares the king passes through (and lands on) must not be attacked
        if hasattr(board, "is_square_attacked") and callable(getattr(board, "is_square_attacked")):
            for f in [at.file] + pass_through_files:
                if board.is_square_attacked(Coordinate(f, y), by_color=self._opponent_color()):
                    return

        # All good — add castle move. Frontend can detect via metadata.
        move = Move(at, Coordinate(landing_file, y), self, metadata={"castle": "K" if kingside else "Q"}) 
        out_moves.append(move)

    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Return only king capture moves (no castling)."""
         # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        captures: List[Move] = []
        for m in self.get_legal_moves(board, at):
            # exclude castling and non-captures
            if getattr(m, "metadata", None) and m.metadata.get("castle"):
                continue
            if board.piece_at_coord(Coordinate(m.to_sq.file, m.to_sq.rank)) is not None:
                captures.append(m)
        return captures

    def mark_moved(self):
        """Mark king as having moved (affects castling eligibility)."""
        self._has_moved = True

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation."""
        data = {
            "id": self.id,
            "type": self.piece_type.name,  # "KING"
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
        }

        if include_moves and board is not None:
            moves = (self.get_legal_captures(board, at) if captures_only
                     else self.get_legal_moves(board, at))
            data["moves"] = [
                {
                    "from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                    "to": {"file": m.to_sq.file, "rank": m.to_sq.rank},
                    # King has no promotion; include castle metadata for UI if present
                    "promotion": None,
                    "castle": (m.metadata.get("castle") if getattr(m, "metadata", None) else None),
                }
                for m in moves
            ]
        return data

    def _opponent_color(self) -> Color:
        return Color.WHITE if self.color == Color.BLACK else Color.BLACK



class Queen(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.QUEEN)

    def _directions(self) -> List[Tuple[int, int]]:
        # rook + bishop rays
        return [
            (1, 0), (-1, 0),
            (0, 1), (0, -1),
            (1, 1), (1, -1),
            (-1, 1), (-1, -1),
        ]

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """All pseudo-legal queen moves (no check filtering)."""
        moves: List[Move] = []
        for dx, dy in self._directions():
            x, y = at.file, at.rank
            while True:
                x += dx
                y += dy
                if not board.is_in_bounds(Coordinate(x, y)):
                    break

                target = board.piece_at_coord(Coordinate(x, y))
                to_sq = Coordinate(x, y)

                if target is None:
                    moves.append(Move(at, to_sq, self))
                else:
                    if target.color != self.color:
                        moves.append(Move(at, to_sq, self))  # capture
                    break  # stop ray on first blocker
        return moves

    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Only capture moves for the queen."""
         # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        return [m for m in self.get_legal_moves(board, at)
                if board.piece_at_coord(Coordinate(m.to_sq.file, m.to_sq.rank)) is not None]

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """
        Minimal, frontend-friendly shape. Extend as UI needs (e.g., images).
        """
        payload = {
            "id": self.id,
            "type": self.piece_type.name,   # "QUEEN"
            "color": self.color.name,       # "WHITE"/"BLACK"
            "position": {"file": at.file, "rank": at.rank},
        }
        if include_moves and board is not None:
            moves = (self.get_legal_captures(board, at) if captures_only
                     else self.get_legal_moves(board, at))
            payload["moves"] = [{"from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                                 "to":   {"file": m.to_sq.file,   "rank": m.to_sq.rank}}
                                for m in moves]
        return payload


class Rook(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.ROOK)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        moves: List[Move] = []
        directions = [
            (0, 1),   # up
            (0, -1),  # down
            (1, 0),   # right
            (-1, 0)   # left
        ]

        for df, dr in directions:
            next_coord = at.offset(df, dr)
            while next_coord:
                # check if this Coordinate is valid
                if not next_coord:
                    break
                elif board.is_empty(next_coord): # empty square: can move and continue
                    moves.append(Move(at, next_coord, self))
                # enemy piece: can capture, but stop moving further
                elif board.is_enemy(next_coord, self.color):
                    moves.append(Move(at, next_coord, self))
                    break
                # friendly piece: cannot move past or capture
                else:
                    break

                # Continue in the same direction
                next_coord = next_coord.offset(df, dr)

        return moves

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        """Return only rook capture moves."""
         # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        captures: List[Move] = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        for df, dr in directions:
            next_coord = at.offset(df, dr)
            while next_coord:
                if not next_coord:
                    break
                elif board.is_enemy(next_coord, self.color):
                    captures.append(Move(at, next_coord, self))
                    break  # can't move past captured piece
                elif not board.is_empty(next_coord):
                    break  # friendly piece blocks path
                next_coord = next_coord.offset(df, dr)
        return captures

    def mark_moved(self):
        """Mark king as having moved (affects castling eligibility)."""
        self._has_moved = True


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
                if not next_coord:
                    break
                elif board.is_empty(next_coord): # empty square: can move and continue
                    moves.append(Move(at, next_coord, self))
                # enemy piece: can capture, but stop moving further
                elif board.is_enemy(next_coord, self.color):
                    moves.append(Move(at, next_coord, self))
                    break
                # friendly piece: cannot move past or capture
                else:
                    break

                # Continue in the same direction
                next_coord = next_coord.offset(df, dr)

        return moves

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        """Return only bishop capture moves."""
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        captures: List[Move] = []
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

        for df, dr in directions:
            next_coord = at.offset(df, dr)
            while next_coord:
                if not next_coord:
                    break
                elif board.is_enemy(next_coord, self.color):
                    captures.append(Move(at, next_coord,self))
                    break  # capture, then stop in that direction
                elif not board.is_empty(next_coord):
                    break  # blocked by friendly piece
                next_coord = next_coord.offset(df, dr)
        return captures


class Knight(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.KNIGHT)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        moves: List[Move] = []

        # 8 possible L-shaped jumps
        jumps = [
            (1, 2), (2, 1), (-1, 2), (-2, 1),
            (1, -2), (2, -1), (-1, -2), (-2, -1)
        ]

        for df, dr in jumps:
            new = at.offset(df, dr)
            if not new:
                continue
            # knights can move to any empty square or capture enemy pieces
            elif new and (board.is_empty(new) or board.is_enemy(new, self.color)):
                moves.append(Move(at, new, self))
        return moves

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        """Return only knight capture moves."""
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        captures: List[Move] = []

        jumps = [
            (1, 2), (2, 1), (-1, 2), (-2, 1),
            (1, -2), (2, -1), (-1, -2), (-2, -1)
        ]

        for df, dr in jumps:
            new = at.offset(df, dr)
            if not new:
                continue
            if new and board.is_enemy(new, self.color):
                captures.append(Move(at, new, self))
        return captures


class Pawn(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.PAWN)
        self._has_moved = False  # internal flag for 2-square move logic

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        """
        Generate all legal pawn moves (excluding en passant for now).
        Assumes:
          - board.is_empty(coord) -> bool
          - board.get_piece_at(file, rank) -> Optional[Piece]
          - board.is_in_bounds(file, rank) -> bool
        """
        moves: List[Move] = []
        direction = 1 if self.color == Color.WHITE else -1
        start_rank = 1 if self.color == Color.WHITE else 6
        promotion_rank = 7 if self.color == Color.WHITE else 0

        # --- Forward move (1 square) ---
        one_step = Coordinate(at.file, at.rank + direction)
        if board.is_in_bounds(Coordinate(one_step.file, one_step.rank)) and board.is_empty(one_step):
            move = Move(at, one_step, self)
            # Promotion
            if one_step.rank == promotion_rank:
                move.promotion = "Queen"
            moves.append(move)

            # --- Forward move (2 squares on first move) ---
            two_step = Coordinate(at.file, at.rank + 2 * direction)
            if at.rank == start_rank and board.is_empty(two_step):
                moves.append(Move(at, two_step, self))

        # --- Captures (diagonals) ---
        for file_offset in [-1, 1]:
            target_file = at.file + file_offset
            target_rank = at.rank + direction
            if not board.is_in_bounds(Coordinate(target_file, target_rank)):
                continue

            target_piece = board.piece_at_coord(Coordinate(target_file, target_rank))
            if target_piece and target_piece.color != self.color:
                move = Move(at, Coordinate(target_file, target_rank), self)
                # Promotion capture
                if target_rank == promotion_rank:
                    move.promotion = "Queen"
                moves.append(move)

        return moves

    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Return only pawn capture moves."""
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []

        return [
            m for m in self.get_legal_moves(board, at)
            if board.piece_at_coord(Coordinate(m.to_sq.file, m.to_sq.rank)) is not None
        ]

    def mark_moved(self):
        """Set flag that pawn has moved (for two-step logic)."""
        self._has_moved = True

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation."""
        data = {
            "id": self.id,
            "type": self.piece_type.name,  # "PAWN"
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
        }

        if include_moves and board is not None:
            moves = (self.get_legal_captures(board, at) if captures_only
                     else self.get_legal_moves(board, at))
            data["moves"] = [
                {
                    "from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                    "to": {"file": m.to_sq.file, "rank": m.to_sq.rank},
                    "promotion": getattr(m, "promotion", None),
                }
                for m in moves
            ]
        return data

class Peon(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.PEON)
        self._has_moved = False
        self._backwards_unlocked = False  # Becomes True after reaching the furthest rank

    def mark_moved(self):
        """Mark that this Peon has moved at least once."""
        self._has_moved = True

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        """
        Peons behave like pawns but:
          - Cannot promote.
          - May move 1 or 2 squares forward initially.
          - Always capture diagonally forward.
          - Permanently gain ability to move & capture backward after reaching the furthest rank.
        """
        moves: List[Move] = []
        direction = 1 if self.color == Color.WHITE else -1
        furthest_rank = 7 if self.color == Color.WHITE else 0

        # --- Forward 1 square ---
        one_step = Coordinate(at.file, at.rank + direction)
        if board.is_in_bounds(one_step) and board.is_empty(one_step):
            moves.append(Move(at, one_step, self))

            # --- Forward 2 squares (only if not moved yet and both empty) ---
            if not self._has_moved:
                two_step = Coordinate(at.file, at.rank + 2 * direction)
                if board.is_in_bounds(two_step) and board.is_empty(two_step):
                    moves.append(Move(at, two_step, self))

        # --- Forward diagonal captures ---
        for file_offset in [-1, 1]:
            target = Coordinate(at.file + file_offset, at.rank + direction)
            if board.is_in_bounds(target) and board.is_enemy(target, self.color):
                moves.append(Move(at, target, self))

        # --- Unlock permanent backward movement/captures ---
        if at.rank == furthest_rank:
            self._backwards_unlocked = True

        # --- Backward movement & captures (if unlocked) ---
        if self._backwards_unlocked:
            # 1 square backward move
            back_one = Coordinate(at.file, at.rank - direction)
            if board.is_in_bounds(back_one) and board.is_empty(back_one):
                moves.append(Move(at, back_one, self))

            # Backward diagonal captures
            for file_offset in [-1, 1]:
                back_target = Coordinate(at.file + file_offset, at.rank - direction)
                if board.is_in_bounds(back_target) and board.is_enemy(back_target, self.color):
                    moves.append(Move(at, back_target, self))

        return moves

    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Return only capture moves for the Peon."""
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []

        captures: List[Move] = []
        direction = 1 if self.color == Color.WHITE else -1
        furthest_rank = 7 if self.color == Color.WHITE else 0

        # --- Forward diagonal captures ---
        for file_offset in [-1, 1]:
            target = Coordinate(at.file + file_offset, at.rank + direction)
            if board.is_in_bounds(target) and board.is_enemy(target, self.color):
                captures.append(Move(at, target, self))

        # --- Unlock permanent backward capture ability ---
        if at.rank == furthest_rank:
            self._backwards_unlocked = True

        # --- Backward diagonal captures (if unlocked) ---
        if self._backwards_unlocked:
            for file_offset in [-1, 1]:
                back_target = Coordinate(at.file + file_offset, at.rank - direction)
                if board.is_in_bounds(back_target) and board.is_enemy(back_target, self.color):
                    captures.append(Move(at, back_target, self))

        return captures

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: Board = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation of Peon, including backward unlock status."""
        data = {
            "id": self.id,
            "type": self.type.name,        # "PEON"
            "color": self.color.name,      # "WHITE"/"BLACK"
            "position": {"file": at.file, "rank": at.rank},
            "backwardsUnlocked": self._backwards_unlocked,
        }

        if include_moves and board is not None:
            moves = (self.get_legal_captures(board, at) if captures_only
                     else self.get_legal_moves(board, at))
            data["moves"] = [
                {
                    "from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                    "to": {"file": m.to_sq.file, "rank": m.to_sq.rank},
                }
                for m in moves
            ]
        return data


class Scout(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.SCOUT)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        """
        Scouts can move like a queen, but up to 5 squares only.
        If the destination contains an enemy piece, the Scout marks it
        and stays in its current location instead of moving.
        """
        moves: List[Move] = []
        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]

        for dx, dy in directions:
            x, y = at.file, at.rank
            for _ in range(5):  # limit to 5 squares
                x += dx
                y += dy
                next_coord = Coordinate(x, y)
                if not board.is_in_bounds(next_coord):
                    break

                if board.is_empty(next_coord):
                    moves.append(Move(at, next_coord, self))
                    continue

                # Enemy piece encountered → mark, stay in place
                if board.is_enemy(next_coord, self.color):
                    move = Move(at, next_coord, self, metadata={"mark": True}) 
                    break

                # Friendly piece blocks further movement
                break

        return moves

    def get_legal_captures(self, board: 'Board', at: Coordinate) -> List[Move]:
        """Scouts do not perform normal captures."""
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []

        return []

    @staticmethod
    def mark_target(board: 'Board', target: Coordinate):
        """Marks the target enemy piece, clearing any existing marks."""
        for piece in board.squares.values():
            piece.marked = False  # clear previous marks
        target_piece = board.piece_at_coord(target)
        if target_piece:
            target_piece.marked = True
            print(f"Marked piece: {target_piece.id} at {target.file},{target.rank}")

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """
        Frontend-friendly dictionary including move options and markable targets.
        """
        data = {
            "id": self.id,
            "type": self.type.name,
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
            "marked": self.marked
        }

        if include_moves and board is not None:
            data["moves"] = [
                {
                    "from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                    "to": {"file": m.to_sq.file, "rank": m.to_sq.rank},
                    "mark": getattr(m, "metadata", {}).get("mark", False),
                    "target": getattr(m, "metadata", {}).get("target", None)
                }
                for m in self.get_legal_moves(board, at)
            ]
        return data

class HeadHunter(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.HEADHUNTER)

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        moves: List[Move] = []
        directions = [
            (-1, -1), (0, -1), (1, -1),
            (-1,  0),          (1,  0),
            (-1,  1), (0,  1), (1,  1),
        ]

        for dx, dy in directions:
            new = Coordinate(at.file + dx, at.rank + dy)
            if not board.is_in_bounds(new):
                continue
            if board.is_empty(new) or board.is_enemy(new, self.color):
                moves.append(Move(at, new, self))
        return moves

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        captures: List[Move] = []
        direction = 1 if self.color == Color.WHITE else -1

        # --- Melee captures (adjacent squares) ---
        adjacent_dirs = [
            (-1, -1), (0, -1), (1, -1),
            (-1,  0),          (1,  0),
            (-1,  1), (0,  1), (1,  1),
        ]
        for dx, dy in adjacent_dirs:
            target = Coordinate(at.file + dx, at.rank + dy)
            if board.is_in_bounds(target) and board.is_enemy(target, self.color):
                captures.append(Move(at, target, self))

        # --- Ranged capture (exactly 3 forward) ---
        target = Coordinate(at.file, at.rank + (3 * direction))
        if board.is_in_bounds(target):
            # check path squares (1 and 2 ahead)
            blocked = any(
                not board.is_empty(Coordinate(at.file, at.rank + (i * direction)))
                for i in [1, 2]
            )
            if not blocked and board.is_enemy(target, self.color):
                captures.append(Move(at, target, self))

        return captures


class Witch(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.WITCH)

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        return [] # implement later

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return [] # Don't remove this check, as it is important for the game rules.
        return [] # implement later


class Warlock(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.WARLOCK)

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        return [] # implement later

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return [] # Don't remove this check, as it is important for the game rules.
        
        return [] # implement later


class Cleric(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.CLERIC)

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        return [] # implement later

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return [] # Don't remove this check, as it is important for the game rules.

        return [] # implement later
        

class DarkLord(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.DARKLORD)

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        return [] # implement later

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return [] # Don't remove this check, as it is important for the game rules.
        
        return [] # implement later

# ---------- Test ----------
print("\n--- Testing Queen ---")
if __name__ == "__main__":
    from backend.enums import Color
    from backend.chess.coordinate import Coordinate

    class _MockType:
        value = "X"
    class _MockPiece:
        def __init__(self, color):
            self.color = color
            self.type = _MockType()

    class _BoardStub:
        """
        Lightweight test implementation of Board.
        Supports:
          - Piece placement, removal, and movement
          - Capture handling
          - is_in_bounds, is_empty, is_enemy, is_frendly
          - is_square_attacked for check/castling tests
        """
    
        def __init__(self, size: int = 8):
            self.size = size
            self.grid = [[None for _ in range(size)] for _ in range(size)]
            self.captured = []
            
        # --------------------------------------------------------
        # Core Board-Like API
        # --------------------------------------------------------
        def piece_at_coord(self, coord: Coordinate):
            """Return the piece at a coordinate or None."""
            if not self.is_in_bounds(coord):
                raise ValueError(f"Out of bounds: {coord}")
            return self.grid[coord.file][coord.rank]
    
        def place(self, f: int, r: int, piece):
            """Place a piece directly at (file, rank)."""
            if not (0 <= f < self.size and 0 <= r < self.size):
                raise ValueError(f"Invalid placement ({f}, {r})")
            self.grid[f][r] = piece
    
        def remove(self, coord: Coordinate):
            """Remove a piece from a square."""
            if self.is_in_bounds(coord):
                self.grid[coord.file][coord.rank] = None
    
        # --------------------------------------------------------
        # Movement Logic (mimics real Board.move_piece)
        # --------------------------------------------------------
        def move_piece(self, move: Move):
            """
            Move a piece from source → destination.
            Returns captured piece if any.
            """
            src, dest = move.from_sq, move.to_sq
            moving_piece = self.piece_at_coord(src)
            if not moving_piece:
                raise ValueError(f"No piece at {src.file},{src.rank}")
    
            captured = self.piece_at_coord(dest)
            if captured:
                self.captured.append(captured)
            self.remove(src)
            self.place(dest.file, dest.rank, moving_piece)
            moving_piece.has_moved = True
            return captured
    
        # --------------------------------------------------------
        # Board State Helpers
        # --------------------------------------------------------
        def is_in_bounds(self, coord: Coordinate) -> bool:
            """Check if coord is inside the board."""
            return 0 <= coord.file < self.size and 0 <= coord.rank < self.size
    
        def is_empty(self, coord: Coordinate) -> bool:
            if not self.is_in_bounds(coord):
                return False
            return self.piece_at_coord(coord) is None
    
        def is_enemy(self, coord: Coordinate, color: Color) -> bool:
            """True if square has an opposing piece."""
            piece = self.piece_at_coord(coord)
            return piece is not None and getattr(piece, "color", None) != color
    
        def is_frendly(self, coord: Coordinate, color: Color) -> bool:
            """True if square has a friendly piece."""
            piece = self.piece_at_coord(coord)
            return piece is not None and getattr(piece, "color", None) == color
    
        # --------------------------------------------------------
        # Attack Detection (used by King and in_check tests)
        # --------------------------------------------------------
        def is_square_attacked(self, coord: Coordinate, by_color: Color) -> bool:
            """
            Returns True if any piece of 'by_color' can capture this coordinate.
            """
            for f in range(self.size):
                for r in range(self.size):
                    piece = self.grid[f][r]
                    if piece and getattr(piece, "color", None) == by_color:
                        try:
                            captures = piece.get_legal_captures(self, Coordinate(f, r))
                            if any(m.to_sq == coord for m in captures):
                                return True
                        except Exception:
                            continue
            return False
    
        # --------------------------------------------------------
        # Utility: list all pieces
        # --------------------------------------------------------
        def all_pieces(self):
            """Return list of (Coordinate, Piece)."""
            out = []
            for f in range(self.size):
                for r in range(self.size):
                    piece = self.grid[f][r]
                    if piece:
                        out.append((Coordinate(f, r), piece))
            return out
    
        # --------------------------------------------------------
        # Debug Helpers
        # --------------------------------------------------------
        def print_board(self):
            """Print simple ASCII representation (top-down)."""
            for r in reversed(range(self.size)):
                row = []
                for f in range(self.size):
                    piece = self.grid[f][r]
                    if piece:
                        row.append(piece.type.value)
                    else:
                        row.append(".")
                print(" ".join(row))
            print()

# -------------------------------------------------------------------------
    print("\n--- Testing Queen ---")
    board = _BoardStub()
    queen = Queen("Q1", Color.WHITE)
    at = Coordinate(3, 3)
    board.place(at.file, at.rank, queen)
    board.place(5, 5, _MockPiece(Color.BLACK))  # enemy capture

    moves = queen.get_legal_moves(board, at)
    captures = queen.get_legal_captures(board, at)
    print(f"Queen total moves: {len(moves)}")
    print("Queen capture squares:", [(m.to_sq.file, m.to_sq.rank) for m in captures])

    assert any((m.to_sq.file, m.to_sq.rank) == (5, 5) for m in captures), "Queen failed to capture diagonal enemy"
# -------------------------------------------------------------------------
    print("\n--- Testing Pawn ---")
    board = _BoardStub()
    pawn = Pawn("P1", Color.WHITE)
    at = Coordinate(3, 6)
    board.place(at.file, at.rank, pawn)
    board.place(2, 7, _MockPiece(Color.BLACK))  # left diag capture
    board.place(4, 7, _MockPiece(Color.BLACK))  # right diag capture

    moves = pawn.get_legal_moves(board, at)
    captures = pawn.get_legal_captures(board, at)
    print(f"Pawn total moves: {len(moves)}")
    print("Pawn capture squares:", [(m.to_sq.file, m.to_sq.rank) for m in captures])

    assert any((m.to_sq.file, m.to_sq.rank) == (2, 7) for m in captures), "Pawn failed left diagonal capture"
    assert any((m.to_sq.file, m.to_sq.rank) == (4, 7) for m in captures), "Pawn failed right diagonal capture"
# -------------------------------------------------------------------------
    print("\n--- Testing King ---")
    board = _BoardStub()
    king = King("K1", Color.WHITE)
    at = Coordinate(4, 0)
    board.place(at.file, at.rank, king)
    board.place(5, 1, _MockPiece(Color.BLACK))  # enemy capture
    board.place(3, 1, _MockPiece(Color.WHITE))  # blocked move

    moves = king.get_legal_moves(board, at)
    captures = king.get_legal_captures(board, at)
    print(f"King total moves: {len(moves)}")
    print("King capture squares:", [(m.to_sq.file, m.to_sq.rank) for m in captures])

    assert all(abs(m.to_sq.file - 4) <= 1 and abs(m.to_sq.rank - 0) <= 1 for m in moves), "King invalid move range"
    assert any((m.to_sq.file, m.to_sq.rank) == (5, 1) for m in captures), "King failed capture test"
# -------------------------------------------------------------------------    
    print("\n--- Testing Rook ---")
    board = _BoardStub()
    rook = Rook("R1", Color.WHITE)
    at = Coordinate(3, 3)
    board.place(at.file, at.rank, rook)
    board.place(3, 6, _MockPiece(Color.BLACK))  # up enemy
    board.place(6, 3, _MockPiece(Color.BLACK))  # right enemy
    board.place(3, 1, _MockPiece(Color.WHITE))  # down block
    board.place(1, 3, _MockPiece(Color.WHITE))  # left block

    moves = rook.get_legal_moves(board, at)
    captures = rook.get_legal_captures(board, at)
    print(f"Rook total moves: {len(moves)}")
    print("Rook capture squares:", [(m.to_sq.file, m.to_sq.rank) for m in captures])

    assert any((m.to_sq.file, m.to_sq.rank) == (3, 6) for m in captures), "Rook failed vertical capture"
    assert any((m.to_sq.file, m.to_sq.rank) == (6, 3) for m in captures), "Rook failed horizontal capture"
# -------------------------------------------------------------------------    
    print("\n--- Testing Bishop ---")
    board = _BoardStub()
    bishop = Bishop("B1", Color.WHITE)
    at = Coordinate(3, 3)
    board.place(at.file, at.rank, bishop)
    board.place(6, 6, _MockPiece(Color.BLACK))  # up-right enemy
    board.place(0, 0, _MockPiece(Color.BLACK))  # down-left enemy
    board.place(5, 1, _MockPiece(Color.WHITE))  # block

    moves = bishop.get_legal_moves(board, at)
    captures = bishop.get_legal_captures(board, at)
    print(f"Bishop total moves: {len(moves)}")
    print("Bishop capture squares:", [(m.to_sq.file, m.to_sq.rank) for m in captures])

    assert any((m.to_sq.file, m.to_sq.rank) == (6, 6) for m in captures), "Bishop failed diagonal capture"
# -------------------------------------------------------------------------    
    print("\n--- Testing Knight ---")
    board = _BoardStub()
    knight = Knight("N1", Color.WHITE)
    at = Coordinate(4, 4)
    board.place(at.file, at.rank, knight)
    board.place(5, 6, _MockPiece(Color.BLACK))  # f7 enemy
    board.place(6, 5, _MockPiece(Color.WHITE))  # g6 block

    moves = knight.get_legal_moves(board, at)
    captures = knight.get_legal_captures(board, at)
    print(f"Knight total moves: {len(moves)}")
    print("Knight capture squares:", [(m.to_sq.file, m.to_sq.rank) for m in captures])

    assert any((m.to_sq.file, m.to_sq.rank) == (5, 6) for m in captures), "Knight failed L-capture"
    assert all(abs(m.to_sq.file - 4) + abs(m.to_sq.rank - 4) in (3,) for m in moves), "Knight move shape invalid"
# -------------------------------------------------------------------------    
    print("\n--- Testing Peon ---")
    board = _BoardStub()
    peon = Peon("PE1", Color.WHITE)
    at = Coordinate(4, 4)  # e5 (middle of the board)
    board.place(at.file, at.rank, peon)
    
    # Place diagonal enemies for forward captures
    board.place(3, 5, _MockPiece(Color.BLACK))  # d6
    board.place(5, 5, _MockPiece(Color.BLACK))  # f6
    
    # Initial movement (no backward unlock)
    moves_initial = peon.get_legal_moves(board, at)
    print("Initial moves:", [(m.to_sq.file, m.to_sq.rank) for m in moves_initial])
    print("Backwards unlocked:", peon._backwards_unlocked)
    print("Initial dict:", peon.to_dict(at, include_moves=True, board=board))
    
    # Move to furthest rank — unlock backward movement
    at_far = Coordinate(4, 7)  # e8
    board = _BoardStub()
    peon._backwards_unlocked = False  # reset manually for clean test
    board.place(at_far.file, at_far.rank, peon)
    
    # Place diagonal enemies for backward captures
    board.place(3, 6, _MockPiece(Color.BLACK))  # d7
    board.place(5, 6, _MockPiece(Color.BLACK))  # f7
    
    moves_unlocked = peon.get_legal_moves(board, at_far)
    print("\nAfter reaching furthest rank:")
    print("Unlocked moves:", [(m.to_sq.file, m.to_sq.rank) for m in moves_unlocked])
    print("Backwards unlocked (flag):", peon._backwards_unlocked)
    print("Unlocked dict:", peon.to_dict(at_far, include_moves=True, board=board))
# -------------------------------------------------------------------------      
    print("\n--- Testing Scout Mark Behavior ---")
    board = Board()
    scout = Scout("S1", Color.WHITE)
    enemy = Rook("R1", Color.BLACK)
    
    board.squares[Coordinate(4, 4)] = scout
    board.squares[Coordinate(6, 6)] = enemy
    
    # Generate moves
    moves = scout.get_legal_moves(board, Coordinate(4, 4))
    mark_moves = [m for m in moves if getattr(m, "metadata", {}).get("mark")]
    
    print(f"Scout has {len(mark_moves)} mark opportunities.")
    for m in mark_moves:
        print("Mark move metadata:", m.metadata)
    
    # Perform a marking move
    if mark_moves:
        board.move_piece(mark_moves[0])
        print("Enemy marked:", enemy.marked)  # Should be True
        print("Scout stays at (4,4):", Coordinate(4, 4) in board.squares)
# -------------------------------------------------------------------------      
    print("\n--- Testing Headhunter ---")
    board = _BoardStub()
    hh = HeadHunter("H1", Color.WHITE)
    pos = Coordinate(4, 3)  # d4

    # Place Headhunter on board
    board.place(4, 3, hh)

    # Case 1: Enemy 3 squares ahead, no blockers
    enemy = _MockPiece(Color.BLACK)
    board.place(4, 6, enemy)

    moves = hh.get_legal_moves(board, pos)
    captures = hh.get_legal_captures(board, pos)

    print(f"Total movement options: {len(moves)} (expect 8)")
    print("Movement targets:", [(m.to_sq.file, m.to_sq.rank) for m in moves])
    print("Capture targets:", [(m.to_sq.file, m.to_sq.rank) for m in captures])

    # Case 2: Blocked attack (piece at distance 1)
    board = _BoardStub()
    board.place(4, 3, hh)
    board.place(4, 4, _MockPiece(Color.WHITE))  # blocker directly ahead
    board.place(4, 6, _MockPiece(Color.BLACK))  # enemy 3 ahead
    blocked_captures = hh.get_legal_captures(board, pos)
    print("Blocked attack (should be none):", [(m.to_sq.file, m.to_sq.rank) for m in blocked_captures])

    # Case 3: Target square empty (no capture)
    board = _BoardStub()
    board.place(4, 3, hh)
    empty_captures = hh.get_legal_captures(board, pos)
    print("Empty target attack (should be none):", [(m.to_sq.file, m.to_sq.rank) for m in empty_captures])

    # Case 4: Black Headhunter attacks downward
    black_hh = HeadHunter("H2", Color.BLACK)
    board = _BoardStub()
    board.place(4, 4, black_hh)
    board.place(4, 1, _MockPiece(Color.WHITE))  # enemy 3 down
    captures_black = black_hh.get_legal_captures(board, Coordinate(4, 4))
    print("Black Headhunter capture:", [(m.to_sq.file, m.to_sq.rank) for m in captures_black])
