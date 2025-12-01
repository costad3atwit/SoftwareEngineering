from __future__ import annotations
from typing import List, Optional, Tuple, TYPE_CHECKING
from backend.enums import Color, PieceType, EffectType
from backend.chess.coordinate import Coordinate
from backend.chess.move import Move
from abc import ABC, abstractmethod
from typing import Tuple

if TYPE_CHECKING:
    from backend.chess.board import Board

class Piece(ABC):
    def __init__(self, id: str, color: Color, piece_type: PieceType, value: int):
        self.id = id
        self.color = color
        self.type = piece_type
        self.value = -1
        self.has_moved = False
        self.marked = False

    def _filter_leaving_forbidden(self, board: Board, at: Coordinate, moves: List[Move]) -> List[Move]:
        """
        Filter out capture moves when leaving Forbidden Lands.
        Rule: Cannot capture while moving from forbidden to non-forbidden territory.
        """
        if not getattr(board, "forbidden_active", False):
            return moves
        
        if not board.is_forbidden(at):
            return moves  # Not in forbidden, so no restriction
        
        # Piece is in Forbidden Lands - filter out captures to non-forbidden squares
        filtered = []
        for move in moves:
            dest = move.to_sq
            is_capture = not board.is_empty(dest)
            dest_forbidden = board.is_forbidden(dest)
            
            # Allow move if:
            # 1. It's not a capture, OR
            # 2. Destination is also in Forbidden Lands
            if not is_capture or dest_forbidden:
                filtered.append(move)
        
        return filtered
    
    def _filter_target_forbidden(self, board: Board, moves: List[Move]) -> List[Move]:
        """
        Remove any capture move whose destination is inside Forbidden Lands.
        Attacker location does not matter for this rule.
        """
        if not getattr(board, "forbidden_active", False):
            return moves
        
        filtered = []
        for move in moves:
            dest = move.to_sq
            # If square contains an enemy AND that square is forbidden → disallowed
            if board.is_forbidden(dest) and board.piece_at_coord(dest) is not None:
                continue
            filtered.append(move)
        return filtered

    @abstractmethod
    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """Return a list of legal moves for this piece."""
        pass
        
    @abstractmethod
    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        """Return a list of legal captures for this piece."""
        pass
    
    def _filter_exhaustion(self, board: Board, at: Coordinate, moves: list[Move]) -> list[Move]:
        """
        If an EXHAUSTION effect is active targeting this piece's color, 
        restrict all moves to Manhattan distance <= 4.
        Otherwise, return moves unchanged.
        """
        # No game state / tracker → no exhaustion
        if not board or not getattr(board, "game_state", None):
            return moves

        tracker = board.game_state.effect_tracker
        from backend.enums import EffectType

        # We assume EffectTracker exposes get_effects_by_type(effect_type)
        effects = tracker.get_effects_by_type(EffectType.EXHAUSTION)
        if not effects:
            return moves

        # This piece is affected if any EXHAUSTION effect targets its color
        affected = False
        for eff in effects:
            # eff.target might be stored as Color or as string
            if eff.target == self.color or getattr(eff, "target", None) == self.color.name:
                affected = True
                break

        if not affected:
            return moves

        # Filter moves by Manhattan distance ≤ 4
        limited: List[Move] = []
        for m in moves:
            d = abs(m.to_sq.file - at.file) + abs(m.to_sq.rank - at.rank)
            if d <= 4:
                limited.append(m)
        return limited

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
            "type": self.type.name,
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
            "marked": self.marked,
            "value": self.value,
        }
        if include_moves and board is not None:
            moves = (self.get_legal_captures(board, at) if captures_only
                     else self.get_legal_moves(board, at))
            payload["moves"] = [{"from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                                 "to":   {"file": m.to_sq.file,   "rank": m.to_sq.rank}}
                                for m in moves]
        return payload


class Effigy(Piece):
    """An inert piece representing a curse anchor."""
    def __init__(self, id: str, color: Color, effect_type: EffectType):
        super().__init__(id, color, PieceType.EFFIGY, value=0)
        self.effect_type = effect_type  # Ties this effigy to the curse that spawned it
        self.effect_id = None  # to be set when effect is created

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return []  # Effigies cannot move

    def get_legal_captures(self, board: 'Board', at: Coordinate) -> List[Move]:
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        return []  # Effigies cannot attack

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """Frontend-friendly representation of Effigy."""
        return {
            "id": self.id,
            "type": self.type.name,
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
            "isEffigy": True,
            "effectType": self.effect_type.value,  # send enum value to frontend
        }

class Barricade(Piece):
    """An uncapturable obstacle that blocks movement for 5 turns."""
    def __init__(self, id: str):
        # Barricades are neutral (no color ownership)
        super().__init__(id, None, PieceType.BARRICADE, value=0)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return []  # Barricades cannot move

    def get_legal_captures(self, board: 'Board', at: Coordinate) -> List[Move]:
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        return []  # Barricades cannot attack

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """Frontend-friendly representation of Barricade."""
        return {
            "id": self.id,
            "type": self.type.name,
            "color": None,
            "position": {"file": at.file, "rank": at.rank},
            "isBarricade": True,
        }

class King(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.KING, value=0)

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

 
        if not self.has_moved:
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
        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

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
        if getattr(rook, "has_moved", False):
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
        captures = self._filter_target_forbidden(board, captures)
        return captures

    def mark_moved(self):
        """Mark king as having moved (affects castling eligibility)."""
        self.has_moved = True

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation."""
        data = {
            "id": self.id,
            "type": self.type.name,
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
        super().__init__(id, color, PieceType.QUEEN, value=9)

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
        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Only capture moves for the queen."""
         # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        captures = [m for m in self.get_legal_moves(board, at)
                if board.piece_at_coord(Coordinate(m.to_sq.file, m.to_sq.rank)) is not None]
        captures = self._filter_target_forbidden(board, captures)
        return captures

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """
        Minimal, frontend-friendly shape. Extend as UI needs (e.g., images).
        """
        payload = {
            "id": self.id,
            "type": self.type.name,   # "QUEEN"
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
        super().__init__(id, color, PieceType.ROOK, value=5)

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

        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

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

        captures = self._filter_target_forbidden(board, captures)
        return captures

    def mark_moved(self):
        """Mark king as having moved (affects castling eligibility)."""
        self.has_moved = True


class Bishop(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.BISHOP, value=3)

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

        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

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

        captures = self._filter_target_forbidden(board, captures)
        return captures


class Knight(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.KNIGHT, value=3)

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

        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

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
        captures = self._filter_target_forbidden(board, captures)
        return captures


class Pawn(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.PAWN, value=1)

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
        promotion_rank = 8 if self.color == Color.WHITE else 1

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
            if not self.has_moved and board.is_empty(two_step):
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

        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Return only pawn capture moves."""
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []

        captures = [
            m for m in self.get_legal_moves(board, at)
            if board.piece_at_coord(Coordinate(m.to_sq.file, m.to_sq.rank)) is not None
        ]
        captures = self._filter_target_forbidden(board, captures)
        return captures

    def mark_moved(self):
        """Set flag that pawn has moved (for two-step logic)."""
        self.has_moved = True

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation."""
        data = {
            "id": self.id,
            "type": self.type.name,  # "PAWN"
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
        super().__init__(id, color, PieceType.PEON, value=1)
        self._backwards_unlocked = False  # Becomes True after reaching the furthest rank

    def mark_moved(self):
        """Mark that this Peon has moved at least once."""
        self.has_moved = True

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
        furthest_rank = 8 if self.color == Color.WHITE else 1

        # --- Forward 1 square ---
        one_step = Coordinate(at.file, at.rank + direction)
        if board.is_in_bounds(one_step) and board.is_empty(one_step):
            moves.append(Move(at, one_step, self))

            # --- Forward 2 squares (only if not moved yet and both empty) ---
            if not self.has_moved:
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

        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

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
        captures = self._filter_target_forbidden(board, captures)
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
        super().__init__(id, color, PieceType.SCOUT, value=3)

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

        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

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
        super().__init__(id, color, PieceType.HEADHUNTER, value=5)

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

        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

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
            if board.is_enemy(target, self.color):
                captures.append(Move(at, target, self))
        captures = self._filter_target_forbidden(board, captures)
        return captures


class Witch(Piece):
    """
    Witch piece that moves 2 squares diagonally or 1 square horizontally.
    Can jump over pieces. When moving off a green tile, spawns a peon.
    Green tiles are created globally when any piece is captured (tracked by Board).
    Value: 5
    """
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.WITCH, value=5)

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """
        Witch movement:
        - 2 squares diagonally in each direction (can jump)
        - 1 square left or right
        """
        moves: List[Move] = []
        
        # Diagonal moves (2 squares in each diagonal direction)
        diagonal_offsets = [
            (2, 2),   # up-right
            (2, -2),  # down-right
            (-2, 2),  # up-left
            (-2, -2)  # down-left
        ]
        
        for df, dr in diagonal_offsets:
            dest = Coordinate(at.file + df, at.rank + dr)
            if not board.is_in_bounds(dest):
                continue
            
            # Can jump, so we don't check intermediate squares
            target = board.piece_at_coord(dest)
            
            # Can move if empty or capture enemy
            if target is None:
                moves.append(Move(at, dest, self))
            elif target.color != self.color:
                moves.append(Move(at, dest, self))
        
        # Horizontal moves (1 square left or right)
        horizontal_offsets = [(1, 0), (-1, 0)]
        
        for df, dr in horizontal_offsets:
            dest = Coordinate(at.file + df, at.rank + dr)
            if not board.is_in_bounds(dest):
                continue
            
            target = board.piece_at_coord(dest)
            
            # Can move if empty or capture enemy
            if target is None:
                moves.append(Move(at, dest, self))
            elif target.color != self.color:
                moves.append(Move(at, dest, self))
        
        # Add metadata about green tile interaction if starting on one
        if hasattr(board, 'green_tiles') and at in board.green_tiles:
            for move in moves:
                move.metadata['leaving_green_tile'] = True
                move.metadata['green_tile_source'] = {'file': at.file, 'rank': at.rank}
        
        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Return only capture moves for the Witch."""
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        captures: List[Move] = []
        
        # Diagonal captures (2 squares)
        diagonal_offsets = [
            (2, 2), (2, -2), (-2, 2), (-2, -2)
        ]
        
        for df, dr in diagonal_offsets:
            dest = Coordinate(at.file + df, at.rank + dr)
            if board.is_in_bounds(dest) and board.is_enemy(dest, self.color):
                captures.append(Move(at, dest, self))
        
        # Horizontal captures (1 square)
        horizontal_offsets = [(1, 0), (-1, 0)]
        
        for df, dr in horizontal_offsets:
            dest = Coordinate(at.file + df, at.rank + dr)
            if board.is_in_bounds(dest) and board.is_enemy(dest, self.color):
                captures.append(Move(at, dest, self))
        
        captures = self._filter_target_forbidden(board, captures)
        return captures
    
    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: Board = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation of Witch."""
        data = {
            "id": self.id,
            "type": self.type.name,
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
            "marked": self.marked,
        }
        
        # Include whether we're on a green tile
        if board and hasattr(board, 'green_tiles'):
            data["on_green_tile"] = at in board.green_tiles
        
        if include_moves and board is not None:
            moves = (self.get_legal_captures(board, at) if captures_only
                     else self.get_legal_moves(board, at))
            data["moves"] = [
                {
                    "from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                    "to": {"file": m.to_sq.file, "rank": m.to_sq.rank},
                    "leaving_green_tile": m.metadata.get('leaving_green_tile', False) if hasattr(m, 'metadata') else False
                }
                for m in moves
            ]
        return data


class Warlock(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.WARLOCK, value=5)
        self.empowered = False  # Set to True when effigy is destroyed

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """
        Warlock movement:
        - Normal mode: Can move to any same-colored tile within 3 Manhattan distance
          along diagonal paths, or 1 tile backwards to change tile color
        - Empowered mode (2 turns after effigy destroyed): Gains knight + rook movement
        """
        moves: List[Move] = []
        
        if self.empowered:
            # Empowered mode: Knight + Rook movement
            moves.extend(self._get_knight_moves(board, at))
            moves.extend(self._get_rook_moves(board, at))
        else:
            # Normal mode: Warlock-specific movement
            moves.extend(self._get_warlock_moves(board, at))
            moves.extend(self._get_backward_move(board, at))
        
        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

    def _get_warlock_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """
        Get warlock's normal diagonal moves within 3 Manhattan distance.
        Must have clear path and land on same-colored square.
        """
        moves: List[Move] = []
        
        # Check if starting square is light or dark
        start_is_light = (at.file + at.rank) % 2 == 0
        
        # All potential warlock destination offsets
        offsets = [
            (1, 1), (1, -1), (-1, 1), (-1, -1),  # 1-step diagonals
            (2, 2), (2, -2), (-2, 2), (-2, -2),  # 2-step diagonals
            (2, 0), (-2, 0), (0, 2), (0, -2)      # 2-step orthogonals
        ]
        
        for df, dr in offsets:
            dest = Coordinate(at.file + df, at.rank + dr)
            
            # Check if destination is in bounds
            if not board.is_in_bounds(dest):
                continue
            
            # All these moves should land on same-colored square
            dest_is_light = (dest.file + dest.rank) % 2 == 0
            if dest_is_light != start_is_light:
                continue
            
            # Check for clear path (diagonal or orthogonal)
            if abs(df) == abs(dr):  # Diagonal move
                if not self._has_clear_diagonal_path(board, at, dest):
                    continue
            else:  # Orthogonal move
                if not self._has_clear_orthogonal_path(board, at, dest):
                    continue
            
            # Check if destination is empty or has enemy piece
            if board.is_empty(dest):
                moves.append(Move(at, dest, self))
            elif board.is_enemy(dest, self.color):
                moves.append(Move(at, dest, self))
        
        return moves

    def _has_clear_diagonal_path(self, board: Board, start: Coordinate, end: Coordinate) -> bool:
        """Check if there's a clear diagonal path between start and end."""
        df = 1 if end.file > start.file else -1 if end.file < start.file else 0
        dr = 1 if end.rank > start.rank else -1 if end.rank < start.rank else 0
        
        # Check all squares between start and end
        current_file = start.file + df
        current_rank = start.rank + dr
        
        while current_file != end.file or current_rank != end.rank:
            check_coord = Coordinate(current_file, current_rank)
            if not board.is_empty(check_coord):
                return False
            current_file += df
            current_rank += dr
        
        return True

    def _has_clear_orthogonal_path(self, board: Board, start: Coordinate, end: Coordinate) -> bool:
        """Check if there's a clear orthogonal path between start and end."""
        df = 1 if end.file > start.file else -1 if end.file < start.file else 0
        dr = 1 if end.rank > start.rank else -1 if end.rank < start.rank else 0
        
        # Check all squares between start and end
        current_file = start.file + df
        current_rank = start.rank + dr
        
        while current_file != end.file or current_rank != end.rank:
            check_coord = Coordinate(current_file, current_rank)
            if not board.is_empty(check_coord):
                return False
            current_file += df
            current_rank += dr
        
        return True

    def _get_backward_move(self, board: Board, at: Coordinate) -> List[Move]:
        """
        Get the one-square backward move to change tile color.
        Backward means towards the warlock's own back rank.
        """
        moves: List[Move] = []
        
        # Determine backward direction (opposite of pawn forward)
        direction = -1 if self.color == Color.WHITE else 1
        
        # One square backward
        dest = Coordinate(at.file, at.rank + direction)
        
        if board.is_in_bounds(dest):
            if board.is_empty(dest):
                moves.append(Move(at, dest, self))
            elif board.is_enemy(dest, self.color):
                moves.append(Move(at, dest, self))
        
        return moves

    def _get_knight_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """Get knight-like moves when empowered."""
        moves: List[Move] = []
        
        # 8 possible L-shaped jumps
        jumps = [
            (1, 2), (2, 1), (-1, 2), (-2, 1),
            (1, -2), (2, -1), (-1, -2), (-2, -1)
        ]
        
        for df, dr in jumps:
            dest = at.offset(df, dr)
            if not dest:
                continue
            if dest and (board.is_empty(dest) or board.is_enemy(dest, self.color)):
                moves.append(Move(at, dest, self))
        
        return moves

    def _get_rook_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """Get rook-like moves when empowered."""
        moves: List[Move] = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for df, dr in directions:
            next_coord = at.offset(df, dr)
            while next_coord:
                if not next_coord:
                    break
                elif board.is_empty(next_coord):
                    moves.append(Move(at, next_coord, self))
                elif board.is_enemy(next_coord, self.color):
                    moves.append(Move(at, next_coord, self))
                    break
                else:
                    break
                next_coord = next_coord.offset(df, dr)
        
        return moves

    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Return only warlock capture moves."""
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return []
        
        captures = [m for m in self.get_legal_moves(board, at)
                if board.piece_at_coord(m.to_sq) is not None]
        captures = self._filter_target_forbidden(board, captures)
        return captures

    def activate_empowerment(self, game_state):
        """Activate empowered mode for 2 turns (called when effigy is destroyed)."""
        from backend.services.effect_tracker import EffectType
        
        self.empowered = True
        
        # Register effect with tracker
        game_state.effect_tracker.add_effect(
            effect_type=EffectType.PIECE_EMPOWERMENT,
            start_turn=game_state.fullmove_number,
            duration=2,
            target=self.id,
            on_expire=lambda e: setattr(self, 'empowered', False)
        )

    def _get_empowered_turns_remaining(self, board) -> int:
        """Get remaining empowered turns from effect tracker."""
        if not board or not hasattr(board, 'game_state'):
            return 0
        
        from backend.services.effect_tracker import EffectType
        effects = board.game_state.effect_tracker.get_effects_by_target(self.id)
        
        for effect in effects:
            if effect.effect_type == EffectType.PIECE_EMPOWERMENT:
                return effect.turns_remaining(board.game_state.fullmove_number)
    
        return 0

    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: Board = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation of Warlock."""
        data = {
            "id": self.id,
            "type": self.type.name,
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
            "marked": self.marked,
            "empowered": self.empowered,
            "empowered_turns": self._get_empowered_turns_remaining(board)
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

class Cleric(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.CLERIC, value=3)
    
    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        moves: List[Move] = []
        
        # Determine forward/backward based on color
        forward_dir = 1 if self.color == Color.WHITE else -1
        backward_dir = -forward_dir
        
        # 1 square forward
        moves.extend(self._try_orthogonal_move(board, at, 0, forward_dir, max_dist=1))
        
        # 2 squares backward
        moves.extend(self._try_orthogonal_move(board, at, 0, backward_dir, max_dist=2))
        
        # 2 squares left
        moves.extend(self._try_orthogonal_move(board, at, -1, 0, max_dist=2))
        
        # 2 squares right
        moves.extend(self._try_orthogonal_move(board, at, 1, 0, max_dist=2))

        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)
    
    def _try_orthogonal_move(self, board: Board, at: Coordinate, 
                            df: int, dr: int, max_dist: int) -> List[Move]:
        """
        Try to move in a direction up to max_dist squares.
        Stops at first blocking piece (friend or foe).
        Only adds moves to empty squares (clerics cannot capture).
        """
        moves: List[Move] = []
        
        for dist in range(1, max_dist + 1):
            dest = Coordinate(at.file + df * dist, at.rank + dr * dist)
            
            # Check if in bounds
            if not board.is_in_bounds(dest):
                break
            
            # Check if square is occupied
            if not board.is_empty(dest):
                break  # Blocked by any piece (friend or foe)
            
            # Empty square - cleric can move here
            moves.append(Move(at, dest, self))
        
        return moves
    
    def get_legal_captures(self, board: Board, at: Coordinate) -> List[Move]:
        """Clerics cannot capture, so this always returns an empty list."""
        return []
    
    def is_protecting(self, at: Coordinate, capture_coord: Coordinate) -> bool:
        """
        Check if a capture at capture_coord is within the cleric's protection range.
        Protection range is a 3-tile Manhattan distance diamond.
        """
        manhattan_dist = abs(capture_coord.file - at.file) + abs(capture_coord.rank - at.rank)
        return 1 <= manhattan_dist <= 3
    
    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: Board = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation of Cleric."""
        data = {
            "id": self.id,
            "type": self.type.name,
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
            "marked": self.marked,
            "value": self.value
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
        

class DarkLord(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.DARKLORD, value=10)
        self.enthralling_target = None
        self.enthralling_progress = 0
        self.daylight_mode = False  # True = hindered (King movement)
    
    # ================================================================
    # === Day/Night Cycle via EffectTracker ==========================
    # ================================================================
    def _start_daylight_cycle(self, game_state):
        """
        Begin a 2-turn daylight (hindered) phase using the EffectTracker.
        When the effect expires, switch back to night mode automatically.
        """
        from backend.services.effect_tracker import EffectType

        self.daylight_mode = True
        game_state.effect_tracker.add_effect(
            effect_type=EffectType.PIECE_EMPOWERMENT,   # reuse the empowerment type
            start_turn=game_state.fullmove_number,
            duration=2,
            target=self.id,
            on_expire=lambda e: setattr(self, "daylight_mode", False)
        )
        print(f"{self.id} is now hindered by daylight for 2 turns.")

    def _ensure_daylight_effect(self, board: "Board"):
        """
        Ensures the correct daylight/night effect is active according to the global turn cycle.
        Called each time get_legal_moves() runs.
        """
        if not board or not hasattr(board, "game_state") or not board.game_state:
            return

        gs = board.game_state
        # every 4 turns -> 2 dark (night) + 2 daylight
        cycle_pos = gs.fullmove_number % 4

        # If it's time for daylight but not already active, start a new 2-turn effect
        if cycle_pos in (2, 3) and not self.daylight_mode:
            self._start_daylight_cycle(gs)
        # Otherwise, stay in night mode
        elif cycle_pos in (0, 1) and self.daylight_mode:
            self.daylight_mode = False

    def check_death_condition(self, board: "Board"):
        """If total enemy material ≤ 10, Dark Lord dies."""
        total_enemy_value = sum(
            getattr(p, "value", 1) for p in board.squares.values() if p.color != self.color
        )
        if total_enemy_value <= 10:
            coord_to_remove = next(
                (coord for coord, piece in board.squares.items() if piece is self),
                None
            )
            if coord_to_remove:
                del board.squares[coord_to_remove]
                print(f"{self.id} perished — enemy strength too weak (≤10).")

    def get_legal_moves(self, board: Board, at: Coordinate) -> List[Move]:
        """
        Moves like a Queen by default.
        Every 2 turns (daylight), hindered to move like a King.
        """
        moves: List[Move] = []
        self._ensure_daylight_effect(board)

        if self.daylight_mode:
            # --- Move like a King ---
            steps = [
                (-1, -1), (0, -1), (1, -1),
                (-1,  0),          (1,  0),
                (-1,  1), (0,  1), (1,  1),
            ]
            for dx, dy in steps:
                dest = Coordinate(at.file + dx, at.rank + dy)
                if not board.is_in_bounds(dest):
                    continue
                if board.is_empty(dest) or board.is_enemy(dest, self.color):
                    moves.append(Move(at, dest, self))
        else:
            # --- Move like a Queen ---
            directions = [
                (1, 0), (-1, 0),
                (0, 1), (0, -1),
                (1, 1), (1, -1),
                (-1, 1), (-1, -1),
            ]
            for df, dr in directions:
                next_coord = at.offset(df, dr)
                while next_coord and board.is_in_bounds(next_coord):
                    if board.is_empty(next_coord):
                        moves.append(Move(at, next_coord, self))
                    elif board.is_enemy(next_coord, self.color):
                        moves.append(Move(at, next_coord, self))
                        break
                    else:
                        break
                    next_coord = next_coord.offset(df, dr)
                    
        # Filter forbidden land exit captures
        moves = self._filter_leaving_forbidden(board, at, moves)
        return self._filter_exhaustion(board, at, moves)

    def get_legal_captures(self, board: Board, at:Coordinate) -> List[Move]:
        # --- Forbidden Lands rule: cannot capture from inside Forbidden Lands ---
        if getattr(board, "forbidden_active", False) and board.is_forbidden(at):
            return [] 
        
        # captures same as moves that land on enemy pieces
        captures = []
        for m in self.get_legal_moves(board, at):
            target_piece = board.piece_at_coord(m.to_sq)
            if target_piece and target_piece.color != self.color:
                captures.append(m)
        
        captures = self._filter_target_forbidden(board, captures)
        return captures
    
    # --- Enthralling Mechanic ---
    def possible_enthrall_targets(self, board: Board, at: Coordinate) -> List[Coordinate]:
        """Return enemy pieces within 1 tile radius that can be enthralled."""
        targets = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                pos = Coordinate(at.file + dx, at.rank + dy)
                if not board.is_in_bounds(pos):
                    continue
                piece = board.piece_at_coord(pos)
                if piece and piece.color != self.color:
                    targets.append(pos)
        return targets

    def start_enthralling(self, board: Board, target: Coordinate):
        """Begin enthralling a nearby enemy piece."""
        target_piece = board.piece_at_coord(target)
        if not target_piece or target_piece.color == self.color:
            raise ValueError("No valid enemy target to enthrall.")
        self.enthralling_target = target
        self.enthralling_progress = 0
        print(f"{self.id} has begun enthralling {target_piece.id} at {target.file},{target.rank}")

    def progress_enthralling(self, board: Board):
        """Advance enthrallment by 1 turn; convert target after 2 turns."""
        if not self.enthralling_target:
            return
        target_piece = board.piece_at_coord(self.enthralling_target)
        if not target_piece:
            self.cancel_enthralling()
            return

        self.enthralling_progress += 1
        print(f"{self.id} is enthralling {target_piece.id} (turn {self.enthralling_progress}/2)")
        if self.enthralling_progress >= 2:
            target_piece.color = self.color
            self.cancel_enthralling()
            print(f"{target_piece.id} has been enthralled and is now friendly!")

    def cancel_enthralling(self):
        """Cancel enthralling process."""
        if self.enthralling_target:
            print(f"{self.id}'s enthralling of {self.enthralling_target} was cancelled.")
        self.enthralling_target = None
        self.enthralling_progress = 0
    
    # --- Dictionary Representation ---
    def to_dict(self, at: Coordinate, include_moves: bool = False,
                board: 'Board' = None, captures_only: bool = False) -> dict:
        """Frontend-friendly dictionary representation."""
        data = {
            "id": self.id,
            "type": self.type.name,
            "color": self.color.name,
            "position": {"file": at.file, "rank": at.rank},
            "daylightMode": self.daylight_mode,
            "enthrallingTarget": (
                {"file": self.enthralling_target.file, "rank": self.enthralling_target.rank}
                if self.enthralling_target else None
            ),
            "enthrallingProgress": self.enthralling_progress,
            "value": self.value,
        }

        if board and hasattr(board, "game_state"):
            turn = board.game_state.fullmove_number
            data["daylightTurnsRemaining"] = 2 - (turn % 2)

        if include_moves and board is not None:
            moves = (
                self.get_legal_captures(board, at)
                if captures_only
                else self.get_legal_moves(board, at)
            )
            data["moves"] = [
                {"from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                 "to": {"file": m.to_sq.file, "rank": m.to_sq.rank}}
                for m in moves
            ]
        return data

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
                        row.append(piece.type.name)
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
