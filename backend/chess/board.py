from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING
from backend.chess.coordinate import Coordinate
from backend.chess.piece import Piece, King, Queen, Rook, Bishop, Knight, Pawn, Scout, Peon, Cleric, Warlock, Witch, HeadHunter, DarkLord
from backend.chess.move import Move
from backend.enums import Color, PieceType, EffectType
import copy

class Board:
    def __init__(self):
        self.squares: Dict[Coordinate, Piece] = {}
        self.dmzActive = False
        self.forbidden_active = False
        self.forbidden_positions = set()
        self.mines = []
        self.glue_tiles = []     # List of dicts: {"coord": Coordinate, "owner": Color, "timer": int}
        self.glued_pieces = {}   # { piece_id: turns_remaining }
        self.green_tiles: Dict[Coordinate, int] = {}
        self.game_state = None

    # ================================================================
    # Forbidden Lands Mechanics
    # ================================================================
    def activate_forbidden_lands(self):
        """
        Expands the board to 10x10 and marks the outer ring as forbidden.
        Pieces inside Forbidden Lands cannot be captured.
        """
        self.dmzActive = True
        self.forbidden_active = True

        # mark outer ring
        self.forbidden_positions = set()
        for file in range(10):
            for rank in range(10):
                if file in (0, 9) or rank in (0, 9):
                    self.forbidden_positions.add(Coordinate(file, rank))
    
    def is_forbidden(self, coord: Coordinate) -> bool:
        """Return True if this coordinate lies within the forbidden ring."""
        return self.forbidden_active and coord in self.forbidden_positions
                    
    def dmz_Activate(self):
        """
        Help change the set up of board to 10x10
        by changing dmzActive to True
        """
        self.dmzActive = True

    # ================================================================
    # Mine Mechanics
    # ================================================================
    def place_mine(self, coord: Coordinate, owner_color: Color):
        """Place a mine on the board with a 4-turn lifespan."""
        self.mines.append({"coord": coord, "owner": owner_color, "timer": 4})
        print(f"Mine placed at {coord.file},{coord.rank} by {owner_color.name}")

    def remove_mine(self, coordinate: Coordinate):
        """Remove a mine at the specified coordinate."""
        self.mines = [m for m in self.mines if m["coord"] != coordinate]
        print(f"Mine at {coordinate.to_algebraic()} removed from board")

    def explode_mine(self, coordinate: Coordinate):
        '''Explode mine at coordinate, capturing nearby pieces'''
        # Capture all pieces within 1 tile radius except kings
        for file_offset in [-1, 0, 1]:
            for rank_offset in [-1, 0, 1]:
                target = Coordinate(coordinate.file + file_offset, 
                                coordinate.rank + rank_offset)
                if target in self.squares:
                    piece = self.squares[target]
                    if piece.type != PieceType.KING:
                        del self.squares[target]
                        print(f"Mine explosion captured {piece.id}")
        
        # Remove mine from board
        self.remove_mine(coordinate)

    def check_mine_trigger(self, dest: Coordinate):
        """Check if a move lands on a mine and trigger explosion if so."""
        for mine in list(self.mines):
            if mine["coord"] == dest:
                self.explode_mine(mine["coord"])
                break

    # ================================================================
    # Glue Mechanics
    # ================================================================
    def place_glue(self, coord: Coordinate, owner_color: Color):
        """Place a glue tile with a 4-turn lifespan."""
        self.glue_tiles.append({"coord": coord, "owner": owner_color, "timer": 4})
        print(f"Glue placed at {coord.file},{coord.rank} by {owner_color.name}")

    def remove_glue(self, coordinate: Coordinate):
        """Remove dried glue from coordinate."""
        self.glue_tiles = [g for g in self.glue_tiles if g["coord"] != coordinate]
        print(f"Glue at {coordinate.to_algebraic()} has been removed")

    def check_glue_trigger(self, dest: Coordinate, moving_piece: 'Piece'):
        """Check if the destination has glue and apply effect."""
        for glue in list(self.glue_tiles):
            if glue["coord"] == dest:
                print(f"Piece {moving_piece.id} stepped on glue at {dest.file},{dest.rank}!")
                
                if self.game_state:
                    from backend.services.effect_tracker import EffectType
                    
                    def release_piece(effect):
                        print(f"Piece {effect.target} is no longer glued.")
                    
                    self.game_state.effect_tracker.add_effect(
                        effect_type=EffectType.PIECE_IMMOBILIZED,
                        start_turn=self.game_state.fullmove_number,
                        duration=2,
                        target=moving_piece.id,
                        metadata={'piece_id': moving_piece.id},
                        on_expire=release_piece
                    )
                else:
                    self.glued_pieces[moving_piece.id] = 2
                
                self.glue_tiles.remove(glue)
                break

    def apply_capture_glue(self, captor: 'Piece', captured: 'Piece'):
        """When a glued piece is captured, captor becomes glued."""
        if captured.id in self.glued_pieces:
            print(f"Captor {captor.id} glued for 2 turns (captured glued piece).")
            self.glued_pieces[captor.id] = 2
            del self.glued_pieces[captured.id]
    
    def tick_traps(self):
        """Advance all trap timers (mines and glue) by one turn and remove expired ones."""
        # Tick down mines
        expired_mines = []
        for mine in list(self.mines):
            mine["timer"] -= 1
            if mine["timer"] <= 0:
                expired_mines.append(mine)
        for mine in expired_mines:
            print(f"Mine at {mine['coord'].to_algebraic()} dismantled (timer expired).")
            self.remove_mine(mine["coord"])
    
        # Tick down glue tiles
        expired_glue = []
        for glue in list(self.glue_tiles):
            glue["timer"] -= 1
            if glue["timer"] <= 0:
                expired_glue.append(glue)
        for glue in expired_glue:
            print(f"Glue at {glue['coord'].to_algebraic()} dried up.")
            self.remove_glue(glue["coord"])
    
        # Tick glued pieces
        to_release = []
        for pid, turns in self.glued_pieces.items():
            self.glued_pieces[pid] = turns - 1
            if self.glued_pieces[pid] <= 0:
                to_release.append(pid)
        for pid in to_release:
            del self.glued_pieces[pid]
            print(f"Piece {pid} is no longer glued.")
    
    def is_glued(self, piece: 'Piece') -> bool:
        # Local glue (legacy)
        if piece.id in self.glued_pieces:
            return True
    
        # EffectTracker-based glue
        if self.game_state:
            for ef in self.game_state.effect_tracker.get_effects_by_target(piece.id):
                if ef.effect_type == EffectType.PIECE_IMMOBILIZED:
                    return True
    
        return False
    
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
        if not self.is_in_bounds(coord):
            return False  # Out of bounds squares are not empty (they don't exist)
        return coord not in self.squares

    def is_enemy(self, coord: Coordinate, color: Color) -> bool:
        """Return True if the coordinate contains an enemy piece and is capturable."""
        if not self.is_in_bounds(coord):
            return False
        if self.forbidden_active and coord in self.forbidden_positions:
            return False  # cannot capture pieces inside Forbidden Lands
        piece = self.squares.get(coord)

        if piece is None:
            return False
        
        #Barricades cannot be captured
        if piece.type == PieceType.BARRICADE:
            return False
        return piece is not None and piece.color != color

    def is_frendly(self, coord: Coordinate, color: Color) -> bool:
        """Return True if the coordinate contains a friendly piece."""
        if not self.is_in_bounds(coord):
            return False  # Out of bounds squares have no friendly piece
        piece = self.squares.get(coord)
        return piece is not None and piece.color == color
    

    def move_piece(self, move: Move) -> Optional[Piece]:
        src, dest = move.from_sq, move.to_sq
        moving_piece = self.squares.get(src)
        if not moving_piece:
            raise ValueError(f"No piece at {src}")


        # Scouts NEVER capture - any Scout "move" to an enemy piece is a mark action
        target_piece = self.squares.get(dest)
        
        if moving_piece.type == PieceType.SCOUT and target_piece and target_piece.color != moving_piece.color:
            print(f"[SCOUT] {moving_piece.id} marking {target_piece.id} at {dest.to_algebraic()}")
            
            # Clear all existing marks
            for piece in self.squares.values():
                if piece:
                    piece.marked = False
            
            # Mark the target (DON'T remove it from board!)
            target_piece.marked = True
            
            # Scout stays in original position - DON'T move it!
            print(f"[SCOUT] {target_piece.id} marked. Scout remains at {src.to_algebraic()}")
            return None  # No capture, Scout didn't move


        # --- Forbidden Lands rules ---
        src_forbidden = self.is_forbidden(src) if self.forbidden_active else False
        dest_forbidden = self.is_forbidden(dest) if self.forbidden_active else False

        captured_piece = None

        if self.forbidden_active:
            # Case 1: destination is forbidden → cannot capture
            if dest_forbidden and dest in self.squares:
                raise ValueError("Cannot capture a piece inside Forbidden Lands.")

            # Case 2: leaving Forbidden Lands → cannot capture while exiting
            if src_forbidden and not dest_forbidden and dest in self.squares:
                raise ValueError("Cannot capture while leaving Forbidden Lands.")

            # otherwise, normal capture if not blocked
            if not dest_forbidden and dest in self.squares:
                captured_piece = self.squares.pop(dest)

        else:
            # Forbidden Lands inactive → normal chess capture
            captured_piece = self.squares.pop(dest, None)

        # --- Apply glue from captured piece to capturing piece ---
        if captured_piece:
            self.apply_capture_glue(moving_piece, captured_piece)
        

        if captured_piece:
            # Mark the capture location as a green tile for 6 half-turns (3 full turns)
            self.green_tiles[dest] = 6

        if captured_piece and self._should_cleric_protect(captured_piece, dest):
            protecting_cleric = self._find_protecting_cleric(captured_piece, dest)
            if protecting_cleric:
                # Find cleric's position
                cleric_pos = self._find_piece_position(protecting_cleric)
                if cleric_pos:
                    # Remove cleric from its position
                    self.squares.pop(cleric_pos)
                    # Resurrect the captured piece at cleric's old position
                    self.squares[cleric_pos] = captured_piece
                    # The cleric is now the piece that was "captured"
                    captured_piece = protecting_cleric

        # --- Perform the move ---
        self.squares.pop(src)
        self.squares[dest] = moving_piece
        moving_piece.has_moved = True

        # --- Clear all marks if a capture occurs ---
        if captured_piece:
            for p in self.squares.values():
                p.marked = False
        
        # --- Check for mine trigger at destination ---
        self.check_mine_trigger(dest)

        # --- Check for glue trigger at destination ---
        self.check_glue_trigger(dest, moving_piece)
        
        from backend.chess.piece import Witch, Peon
        if isinstance(moving_piece, Witch):
            if getattr(move, "metadata", {}).get("leaving_green_tile"):
                # Get the source coordinate where the Witch was
                source_info = move.metadata.get("green_tile_source")
                if source_info:
                    source_coord = Coordinate(source_info["file"], source_info["rank"])
                    
                    # Spawn a Peon at the green tile the Witch just left
                    # Only if the tile is now empty
                    if source_coord not in self.squares:
                        import time
                        peon_id = f"peon_{moving_piece.color.name[0].lower()}_{int(time.time() * 1000)}"
                        peon = Peon(peon_id, moving_piece.color)
                        self.squares[source_coord] = peon
        
        return captured_piece

    def is_exhausted(self, color: Color) -> bool:
        """Return True if a global Exhaustion effect is active for the given color."""
        if not self.game_state:
            return False
        tracker = self.game_state.effect_tracker
        effects = tracker.get_effects_by_type(EffectType.EXHAUSTION)
        return any(e.target == color.name for e in effects)

    def _find_piece_position(self, piece: Piece) -> Optional[Coordinate]:
        """Find the coordinate of a specific piece on the board."""
        for coord, board_piece in self.squares.items():
            if board_piece.id == piece.id:
                return coord
        return None

    def _should_cleric_protect(self, captured_piece: Piece, capture_coord: Coordinate) -> bool:
        """
        Check if a captured piece should be protected by a cleric.
        Protection applies if:
        1. Captured piece has value > 1 (greater than pawn)
        2. There's a friendly cleric within range
        """
        from backend.chess.piece import Cleric
        
        # Only protect pieces with value > 1
        if not hasattr(captured_piece, 'value') or captured_piece.value <= 1:
            return False
        
        # Check if there's a protecting cleric
        return self._find_protecting_cleric(captured_piece, capture_coord) is not None

    def _find_protecting_cleric(self, captured_piece: Piece, capture_coord: Coordinate) -> Optional[Piece]:
        """
        Find a friendly cleric that can protect the captured piece.
        Returns the first cleric found within range, or None.
        """
        from backend.chess.piece import Cleric
        
        for coord, piece in self.squares.items():
            # Check if it's a friendly cleric
            if isinstance(piece, Cleric) and piece.color == captured_piece.color:
                # Check if capture happened within cleric's protection range
                if piece.is_protecting(coord, capture_coord):
                    return piece
        
        return None

    def update_green_tiles(self):
        """
        Decrease green tile counters by 1 half-turn.
        Remove expired tiles (when counter reaches 0).
        Should be called at the end of each half-turn.
        """
        expired_tiles = []
        for coord, half_turns_remaining in self.green_tiles.items():
            self.green_tiles[coord] -= 1
            if self.green_tiles[coord] <= 0:
                expired_tiles.append(coord)
        
        # Remove expired tiles
        for coord in expired_tiles:
            del self.green_tiles[coord]
    
    def is_square_attacked(self, coord: Coordinate, by_color: Color) -> bool:
        """
        Return True if the given square is attacked by any piece of the specified color.
        This checks all opposing pieces' capture moves.
        """
        for pos, piece in self.squares.items():
            if piece.color != by_color:
                continue  # only check attackers of the given color
            
            # CRITICAL: Skip the king to avoid infinite recursion
            # Kings don't check if their own moves put them in check
            from backend.enums import PieceType
            if piece.type == PieceType.KING:
                continue

            # Get all capture moves from this piece
            try:
                captures = piece.get_legal_captures(self, pos)
            except Exception:
                # Skip malformed or incomplete pieces
                continue

            # If any capture move targets this square → it's attacked
            for move in captures:
                if move.to_sq == coord:
                    return True
        return False

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
                    if move.to_sq == king_coord:
                        return True
        return False
    
    def place_piece(self, piece: Piece, coord: Coordinate) -> None:
        """Place a piece on the board."""
        if not self.is_in_bounds(coord):
            raise ValueError(f"Cannot place piece outside the board: {coord}")
        self.squares[coord] = piece

    def remove_piece(self, coord: Coordinate) -> None:
        """Remove a piece from a square if present."""
        if coord in self.squares:
            del self.squares[coord]

    def _all_board_coords(self):
        """Generator for all coordinates on the board."""
        max_range = 10 if self.dmzActive else 8
        min_range = 0 if self.dmzActive else 1

        for f in range(min_range, max_range):
            for r in range(min_range, max_range):
                yield Coordinate(f, r)

    def clone(self) -> 'Board':
        """Return a deep copy of the board."""
        new_board = Board()
        new_board.squares = {coord: copy.deepcopy(piece) for coord, piece in self.squares.items()}
        print("Cloning board")
        return new_board

    def to_dict(self, game_state=None) -> dict:
        """
        Convert the current board state into a JSON-serializable dictionary.
        Includes all piece data and board settings for frontend rendering.
        
        Args:
            game_state: Optional GameState to use for filtering legal moves with check validation
        """
        board_data = {
            "dmzActive": self.dmzActive,
            "pieces": []
        }

        # convert each piece to dictionary form
        for coord, piece in self.squares.items():
            try:
                print(f"DEBUG: Serializing {piece.type.name} at {coord.to_algebraic()}")
                
                #Get filtered moves from GameState if available
                if game_state:
                    # Use GameState.legal_moves_for() which includes check filtering
                    legal_moves = game_state.legal_moves_for(coord)
                    # Convert moves to dict format
                    moves_data = [
                        {
                            "from": {"file": m.from_sq.file, "rank": m.from_sq.rank},
                            "to": {"file": m.to_sq.file, "rank": m.to_sq.rank},
                            "promotion": m.promotion,
                            "castle": m.metadata.get("castle") if hasattr(m, "metadata") else None,
                            "mark": m.metadata.get("mark", False) if hasattr(m, "metadata") else False,
                            "stay_in_place": m.metadata.get("stay_in_place", False) if hasattr(m, "metadata") else False
                        }
                        for m in legal_moves
                    ]
                    
                    # Get piece dict without moves, then add filtered moves
                    piece_dict = piece.to_dict(
                        at=coord,
                        include_moves=False,  # Don't generate moves in piece
                        board=self
                    )
                    piece_dict["moves"] = moves_data  # Add pre-filtered moves
                else:
                    # Original behavior: let piece generate its own moves
                    piece_dict = piece.to_dict(
                        at=coord,
                        include_moves=True,
                        board=self   
                    )
                
                # merge an algebraic string (useful for frontend rendering)
                piece_dict["position_algebraic"] = coord.to_algebraic()
                board_data["pieces"].append(piece_dict)
                print(f"DEBUG: Successfully serialized {piece.type.name} at {coord.to_algebraic()}")
            except Exception as e:
                print(f"ERROR: Failed to serialize {piece.type.name} at {coord.to_algebraic()}: {e}")
                import traceback
                traceback.print_exc()
                # Add piece without moves as fallback
                piece_dict = {
                    "id": piece.id,
                    "type": piece.type.value,
                    "color": piece.color.name,
                    "position": {"file": coord.file, "rank": coord.rank},
                    "position_algebraic": coord.to_algebraic(),
                    "marked": piece.marked,
                    "moves": []  # Empty moves on error
                }
                board_data["pieces"].append(piece_dict)
                
        # Include Forbidden Lands info for the frontend
        board_data["forbiddenActive"] = self.forbidden_active
        if self.forbidden_active:
            board_data["forbiddenTiles"] = [
                {"file": coord.file, "rank": coord.rank}
                for coord in self.forbidden_positions
            ]
        else:
            board_data["forbiddenTiles"] = []

        # Include green tiles for frontend rendering
        board_data["greenTiles"] = [
            {
                "file": coord.file,
                "rank": coord.rank,
                "turnsRemaining": half_turns // 2  # Convert half-turns to full turns for display
            }
            for coord, half_turns in self.green_tiles.items()
        ]
        
        # Include mine info if present
        board_data["mines"] = [
            {
                "file": m["coord"].file,
                "rank": m["coord"].rank,
                "owner": m["owner"].name,
                "timer": m["timer"],
            }
            for m in self.mines
        ]

        # Include glue tile info
        board_data["glueTiles"] = [
            {
                "file": g["coord"].file,
                "rank": g["coord"].rank,
                "owner": g["owner"].name,
                "timer": g["timer"],
            } for g in self.glue_tiles
        ]

        board_data["gluedPieces"] = list(self.glued_pieces.keys())

        return board_data
#------------------------------
#Inline Test
#------------------------------
if __name__ == "__main__":
    from move import Move
    from coordinate import Coordinate
    from enums import Color

    def print_test(name, passed=True):
        print(f"{'Pass' if passed else 'Fail'} {name}")

    try:
        # --- Test 1: setup_standard places correct number of pieces ---
        board = Board()
        board.setup_standard()
        expected_piece_count = 32  # 16 white + 16 black
        actual_piece_count = len(board.squares)
        print_test("setup_standard places correct number of pieces",
                   actual_piece_count == expected_piece_count)

        # --- Test 2: piece_at_coord retrieves correct piece ---
        coord = Coordinate(5, 1)  # White King position
        piece = board.piece_at_coord(coord)
        print_test("piece_at_coord retrieves correct piece",
                   piece and piece.id == "wK")

        # --- Test 3: is_in_bounds (normal 8x8 area) ---
        inside = Coordinate(5, 5)
        outside = Coordinate(0, 0)
        print_test("is_in_bounds identifies inside coords", board.is_in_bounds(inside))
        print_test("is_in_bounds identifies outside coords", not board.is_in_bounds(outside))

        # --- Test 4: is_empty() correctly identifies empty and occupied squares ---
        empty_coord = Coordinate(5, 5)
        filled_coord = Coordinate(5, 1)  # wK
        print_test("is_empty() works for empty squares", board.is_empty(empty_coord))
        print_test("is_empty() works for occupied squares", not board.is_empty(filled_coord))

        # --- Test 5: is_enemy() and is_frendly() ---
        white_piece = Coordinate(5, 1)
        black_piece = Coordinate(5, 8)
        print_test("is_enemy() detects opposite color",
                   board.is_enemy(black_piece, Color.WHITE))
        print_test("is_frendly() detects same color",
                   board.is_frendly(white_piece, Color.WHITE))

        # --- Test 6: move_piece() moves a piece and returns captured if any ---
        move = Move(Coordinate(5, 1), Coordinate(5, 2))
        captured = board.move_piece(move)
        print_test("move_piece() moves piece to destination",
                   Coordinate(5, 2) in board.squares)
        print_test("move_piece() removes piece from original location",
                   Coordinate(5, 1) not in board.squares)
        print_test("move_piece() returns None when no capture", captured is None)

        # --- Test 7: move_piece() raises ValueError if no piece at source ---
        try:
            board.move_piece(Move(Coordinate(0, 0), Coordinate(1, 1)))
            print_test("move_piece() missing piece check failed", False)
        except ValueError:
            print_test("move_piece() raises ValueError if no piece at source")

        # --- Test 8: clone() produces deep copy ---
        clone_board = board.clone()
        clone_board.move_piece(Move(Coordinate(5, 2), Coordinate(5, 3)))
        print_test("clone() produces independent copy",
                   Coordinate(5, 3) in clone_board.squares and
                   Coordinate(5, 2) not in clone_board.squares and
                   Coordinate(5, 2) in board.squares)

        # --- Test 9: to_dict() includes dmzActive and pieces ---
        data = board.to_dict()
        print_test("to_dict() includes dmzActive key", "dmzActive" in data)
        print_test("to_dict() includes pieces list", isinstance(data["pieces"], list))
        print_test("to_dict() contains valid piece info",
                   all("id" in p and "type" in p and "color" in p for p in data["pieces"]))

        # --- Test 10: in_check_for() runs safely with no check detected ---
        print_test("in_check_for() returns boolean",
                   isinstance(board.in_check_for(Color.WHITE), bool))

        # --- Test 11: dmzActive toggle (manual) ---
        board.dmzActive = True
        inside_dmz = Coordinate(0, 0)
        print_test("is_in_bounds respects DMZ active flag", board.is_in_bounds(inside_dmz))

    except Exception as e:
        print(f"Unexpected test error: {e}")
