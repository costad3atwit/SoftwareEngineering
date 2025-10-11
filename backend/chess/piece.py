class PieceType(Enum):
    KING = "KING"
    QUEEN = "QUEEN"
    ROOK = "ROOK"
    BISHOP = "BISHOP"
    KNIGHT = "KNIGHT"
    PAWN = "PAWN"
class Piece:
    def __init__(self, id: str, color: Color, piece_type: PieceType):
        self.id = id
        self.color = color
        self.type = piece_type
        self.has_moved = False

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        """Return a list of legal moves for this piece."""
        raise NotImplementedError() # implement later

    def clone(self) -> 'Piece':
        """Return a deep copy of the piece."""
        return Piece(self.id, self.color, self.type)


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
        return [] # implement later


class Knight(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.KNIGHT)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later


class Pawn(Piece):
    def __init__(self, id: str, color: Color):
        super().__init__(id, color, PieceType.PAWN)

    def get_legal_moves(self, board: 'Board', at: Coordinate) -> List[Move]:
        return [] # implement later
