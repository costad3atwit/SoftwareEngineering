class Board:
    def __init__(self):
        self.squares: Dict[Coordinate, Piece] = {}

    def setup_standard(self):
        """Set up standard chessboard layout."""
        pass # implement later

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
