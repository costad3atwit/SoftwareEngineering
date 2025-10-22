from enum import Enum

class PieceType(Enum):
    KING = "KING"
    QUEEN = "QUEEN"
    ROOK = "ROOK"
    BISHOP = "BISHOP"
    KNIGHT = "KNIGHT"
    PAWN = "PAWN"
    PEON = "PEON"
    SCOUT = "SCOUT"
    HEADHUNTER = "HEADHUNTER"
    WITCH = "WITCH"
    WARLOCK = "WARLOCK"
    CLERIC = "CLERIC"
    DARKLORD = "DARKLORD"
    
class TargetType(Enum):
    BOARD = "BOARD"
    PIECE = "PIECE"
    TIMER = "TIMER"
    TURN = "TURN"

class CardType(Enum):
    UNSTABLE = "UNSTABLE"
    CURSE = "CURSE"
    HIDDEN = "HIDDEN"
    TRANSFORM = "TRANSFORM"
    FORCED = "FORCED"

class Color(Enum):
    WHITE = 1
    BLACK = 0

class GameStatus(Enum):
    WAITING = "WAITING"
    IN_PROGRESS = "IN PROGRESS"
    CHECK = "CHECK"
    CHECKMATE = "CHECKMATE"
    STALEMATE = "STALEMATE"
    RESIGNED = "RESIGNED"
    DRAW = "DRAW"
