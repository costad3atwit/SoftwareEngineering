class Coordinate:
    file: int # 0-9 column
    rank: int # 0-9 row 

    def __init__(self, file: int, rank: int):
        if not (0 <= file <= 9 and 0 <= rank <= 9):
            raise ValueError(f"Invalid coordinate — must be within 0–7 range.")
        self.file = file
        self.rank = rank

    def __eq__(self, other):
        return isinstance(other, Coordinate) and self.file == other.file and self.rank == other.rank

    def to_algebraic(self) -> str:
        """Convert coordinate to algebraic notation."""
        return f"{chr(self.file + ord('a'))}{self.rank + 1}"

    @staticmethod
    def from_algebraic(notation: str) -> "Coordinate":
        """Create a coordinate from algebraic notation (e.g., 'e4')."""
        file = ord(notation[0]) - ord('a')
        rank = int(notation[1]) - 1
        return Coordinate(file, rank)

    def offset(self, df: int, dr: int):
        """
        Return a new coordinate offset by (df, dr).
        If the result is off the board, return None.
        """
        new_file = self.file + df
        new_rank = self.rank + dr
        if 0 <= new_file <= 7 and 0 <= new_rank <= 7:
            return Coordinate(new_file, new_rank)
        return None

    def __str__(self):
        """Print Coordinates"""
        return self.to_algebraic()
