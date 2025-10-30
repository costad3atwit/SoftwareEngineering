from __future__ import annotations
from typing import Dict, Optional
from backend.chess.coordinate import Coordinate
from backend.chess.piece import Piece, King, Queen, Rook, Bishop, Knight, Pawn
from backend.chess.move import Move
from backend.enums import Color
import copy

class Board:
    def __init__(self):
        self.squares: Dict[Coordinate, Piece] = {}
        self.dmzActive = False

    def dmz_Activate(self):
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

    def to_dict(self) -> dict:
        """
        Convert the current board state into a JSON-serializable dictionary.
        Includes all piece data and board settings for frontend rendering.
        """
        board_data = {
            "dmzActive": self.dmzActive,
            "pieces": []
        }
    
        # convert each piece to dictionary form
        for coord, piece in self.squares.items():
            piece_dict = piece.to_dict(
                at=coord,
                include_moves=True,
                board=self   # provide the board reference for move generation
            )
            # merge an algebraic string (useful for frontend rendering)
            piece_dict["position_algebraic"] = coord.to_algebraic()

            board_data["pieces"].append(piece_dict)

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
