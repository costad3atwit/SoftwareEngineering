from enum import Enum

class PieceType(Enum):
    KING = "K"
    QUEEN = "Q"
    ROOK = "R"
    BISHOP = "B"
    KNIGHT = "N"
    PAWN = "P"
    PEON = "E" #can we find a better name than peon for clarity sake?
    SCOUT = "S"
    HEADHUNTER = "H"
    WITCH = "W" #better name?
    WARLOCK = "W" #Better name?
    CLERIC = "C"
    DARKLORD = "D"
    
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
    WHITE = "W"
    BLACK = "B"

class GameStatus(Enum): 
    WAITING = "WAITING"
    IN_PROGRESS = "IN PROGRESS"
    CHECK = "CHECK"
    CHECKMATE = "CHECKMATE"
    STALEMATE = "STALEMATE"
    RESIGNED = "RESIGNED"
    DRAW = "DRAW"
